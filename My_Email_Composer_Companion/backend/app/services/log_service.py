"""Interaction logging service."""

from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import InteractionLog


class LogService:
    async def create(
        self,
        db: AsyncSession,
        *,
        action: str,
        input_text: str,
        prompt: str,
        llm_response: str,
        provider: str,
        model: str,
        workspace_id: Optional[int] = None,
        context_used: Optional[str] = None,
        final_edited: Optional[str] = None,
        temperature: float = 0.4,
        tokens_used: Optional[int] = None,
        latency_ms: Optional[int] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> InteractionLog:
        log = InteractionLog(
            workspace_id=workspace_id,
            action=action,
            input_text=input_text,
            context_used=context_used,
            prompt=prompt,
            llm_response=llm_response,
            final_edited=final_edited,
            provider=provider,
            model=model,
            temperature=temperature,
            tokens_used=tokens_used,
            latency_ms=latency_ms,
            metadata_json=metadata,
        )
        db.add(log)
        await db.flush()
        return log

    async def list_logs(
        self,
        db: AsyncSession,
        workspace_id: Optional[int] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[InteractionLog]:
        query = select(InteractionLog).order_by(InteractionLog.created_at.desc())
        if workspace_id is not None:
            query = query.where(InteractionLog.workspace_id == workspace_id)
        query = query.offset(offset).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())

    async def get(self, db: AsyncSession, log_id: int) -> Optional[InteractionLog]:
        result = await db.execute(
            select(InteractionLog).where(InteractionLog.id == log_id)
        )
        return result.scalar_one_or_none()
