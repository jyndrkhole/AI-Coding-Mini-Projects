"""LLM provider factory with runtime switching support."""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.database.models import AppSetting
from app.llm.base import BaseLLMProvider, LLMConfig
from app.llm.groq_provider import GroqProvider
from app.llm.ollama_provider import OllamaProvider


async def _get_setting(db: Optional[AsyncSession], key: str, default: str) -> str:
    if db is None:
        return default
    result = await db.execute(select(AppSetting).where(AppSetting.key == key))
    row = result.scalar_one_or_none()
    return row.value if row else default


async def get_llm_provider(
    db: Optional[AsyncSession] = None,
    settings: Optional[Settings] = None,
) -> BaseLLMProvider:
    """Build the active LLM provider from settings / DB overrides."""
    settings = settings or get_settings()

    provider_name = await _get_setting(db, "llm_provider", settings.llm_provider)
    model = await _get_setting(db, "llm_model", settings.llm_model)
    temperature = float(
        await _get_setting(db, "llm_temperature", str(settings.llm_temperature))
    )
    max_tokens = int(
        await _get_setting(db, "llm_max_tokens", str(settings.llm_max_tokens))
    )
    groq_key = await _get_setting(db, "groq_api_key", settings.groq_api_key)
    ollama_url = await _get_setting(db, "ollama_base_url", settings.ollama_base_url)
    ollama_model = await _get_setting(db, "ollama_model", settings.ollama_model)

    if provider_name == "ollama":
        config = LLMConfig(
            provider="ollama",
            model=model if model != settings.llm_model else ollama_model,
            temperature=temperature,
            max_tokens=max_tokens,
            base_url=ollama_url,
        )
        return OllamaProvider(config)

    config = LLMConfig(
        provider="groq",
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        api_key=groq_key or settings.groq_api_key,
        base_url=settings.groq_base_url,
    )
    return GroqProvider(config)


def create_provider_from_config(config: LLMConfig) -> BaseLLMProvider:
    if config.provider == "ollama":
        return OllamaProvider(config)
    if config.provider == "groq":
        return GroqProvider(config)
    raise ValueError(f"Unsupported LLM provider: {config.provider}")
