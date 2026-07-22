"""Dashboard statistics service."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import (
    Document,
    EmailRecord,
    InteractionLog,
    PromptTemplate,
    StyleExample,
    Workspace,
)
from app.schemas import DashboardStats, DocumentOut, EmailOut


class DashboardService:
    async def get_stats(self, db: AsyncSession) -> DashboardStats:
        workspace_count = await db.scalar(select(func.count()).select_from(Workspace)) or 0
        document_count = await db.scalar(select(func.count()).select_from(Document)) or 0
        email_count = await db.scalar(select(func.count()).select_from(EmailRecord)) or 0
        style_count = await db.scalar(select(func.count()).select_from(StyleExample)) or 0
        prompt_count = await db.scalar(select(func.count()).select_from(PromptTemplate)) or 0
        log_count = await db.scalar(select(func.count()).select_from(InteractionLog)) or 0

        emails_result = await db.execute(
            select(EmailRecord).order_by(EmailRecord.created_at.desc()).limit(5)
        )
        docs_result = await db.execute(
            select(Document).order_by(Document.created_at.desc()).limit(5)
        )

        return DashboardStats(
            workspace_count=workspace_count,
            document_count=document_count,
            email_count=email_count,
            style_example_count=style_count,
            prompt_count=prompt_count,
            log_count=log_count,
            recent_emails=[EmailOut.model_validate(e) for e in emails_result.scalars().all()],
            recent_documents=[
                DocumentOut.model_validate(d) for d in docs_result.scalars().all()
            ],
        )
