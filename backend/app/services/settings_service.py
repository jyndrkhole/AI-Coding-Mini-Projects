"""Settings service with DB-backed overrides."""

from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database.models import AppSetting
from app.llm.factory import get_llm_provider
from app.prompts.templates import REPLY_STYLES, REWRITE_MODES
from app.schemas import SettingsOut, SettingsUpdate


SETTING_KEYS = [
    "llm_provider",
    "llm_model",
    "llm_temperature",
    "llm_max_tokens",
    "groq_api_key",
    "ollama_base_url",
    "ollama_model",
    "embedding_provider",
    "embedding_model",
    "chunk_size",
    "chunk_overlap",
    "retrieval_top_k",
]


class SettingsService:
    async def _get_map(self, db: AsyncSession) -> dict[str, str]:
        result = await db.execute(select(AppSetting))
        rows = result.scalars().all()
        return {r.key: r.value for r in rows}

    async def get_value(self, db: AsyncSession, key: str, default: str) -> str:
        result = await db.execute(select(AppSetting).where(AppSetting.key == key))
        row = result.scalar_one_or_none()
        return row.value if row else default

    async def set_value(self, db: AsyncSession, key: str, value: str) -> None:
        result = await db.execute(select(AppSetting).where(AppSetting.key == key))
        row = result.scalar_one_or_none()
        if row:
            row.value = value
        else:
            db.add(AppSetting(key=key, value=value))
        await db.flush()

    async def get_settings(self, db: AsyncSession) -> SettingsOut:
        env = get_settings()
        stored = await self._get_map(db)

        def val(key: str, default: Any) -> Any:
            return stored.get(key, default)

        provider = str(val("llm_provider", env.llm_provider))
        healthy = False
        try:
            llm = await get_llm_provider(db, env)
            healthy = await llm.health_check()
        except Exception:
            healthy = False

        groq_key = str(val("groq_api_key", env.groq_api_key or ""))

        return SettingsOut(
            llm_provider=provider,
            llm_model=str(val("llm_model", env.llm_model)),
            llm_temperature=float(val("llm_temperature", env.llm_temperature)),
            llm_max_tokens=int(val("llm_max_tokens", env.llm_max_tokens)),
            groq_api_key_set=bool(groq_key and groq_key != "your_groq_api_key_here"),
            ollama_base_url=str(val("ollama_base_url", env.ollama_base_url)),
            ollama_model=str(val("ollama_model", env.ollama_model)),
            embedding_provider=str(val("embedding_provider", env.embedding_provider)),
            embedding_model=str(val("embedding_model", env.embedding_model)),
            chunk_size=int(val("chunk_size", env.chunk_size)),
            chunk_overlap=int(val("chunk_overlap", env.chunk_overlap)),
            retrieval_top_k=int(val("retrieval_top_k", env.retrieval_top_k)),
            provider_healthy=healthy,
            available_rewrite_modes=REWRITE_MODES,
            available_reply_styles=REPLY_STYLES,
        )

    async def update_settings(
        self, db: AsyncSession, data: SettingsUpdate
    ) -> SettingsOut:
        payload = data.model_dump(exclude_unset=True)
        for key, value in payload.items():
            if key in SETTING_KEYS and value is not None:
                await self.set_value(db, key, str(value))
        return await self.get_settings(db)
