"""Workspace management service."""

from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Document, EmailRecord, Workspace
from app.rag.vector_store import VectorStore
from app.schemas import WorkspaceCreate, WorkspaceOut, WorkspaceUpdate


class WorkspaceService:
    def __init__(self, vector_store: Optional[VectorStore] = None):
        self.vector_store = vector_store or VectorStore()

    async def ensure_default(self, db: AsyncSession) -> Workspace:
        result = await db.execute(
            select(Workspace).where(Workspace.is_default.is_(True))
        )
        existing = result.scalar_one_or_none()
        if existing:
            return existing

        workspace = Workspace(
            name="Default",
            description="Default personal workspace",
            color="#3b82f6",
            is_default=True,
        )
        db.add(workspace)
        await db.flush()
        return workspace

    async def create(self, db: AsyncSession, data: WorkspaceCreate) -> Workspace:
        workspace = Workspace(
            name=data.name,
            description=data.description,
            color=data.color,
        )
        db.add(workspace)
        await db.flush()
        self.vector_store.get_or_create_collection(workspace.id)
        return workspace

    async def list_workspaces(self, db: AsyncSession) -> list[WorkspaceOut]:
        result = await db.execute(select(Workspace).order_by(Workspace.created_at.asc()))
        workspaces = list(result.scalars().all())
        outputs: list[WorkspaceOut] = []
        for ws in workspaces:
            doc_count = await db.scalar(
                select(func.count()).select_from(Document).where(
                    Document.workspace_id == ws.id
                )
            )
            email_count = await db.scalar(
                select(func.count()).select_from(EmailRecord).where(
                    EmailRecord.workspace_id == ws.id
                )
            )
            outputs.append(
                WorkspaceOut(
                    id=ws.id,
                    name=ws.name,
                    description=ws.description,
                    color=ws.color,
                    is_default=ws.is_default,
                    created_at=ws.created_at,
                    document_count=doc_count or 0,
                    email_count=email_count or 0,
                )
            )
        return outputs

    async def get(self, db: AsyncSession, workspace_id: int) -> Optional[Workspace]:
        result = await db.execute(
            select(Workspace).where(Workspace.id == workspace_id)
        )
        return result.scalar_one_or_none()

    async def update(
        self, db: AsyncSession, workspace_id: int, data: WorkspaceUpdate
    ) -> Optional[Workspace]:
        workspace = await self.get(db, workspace_id)
        if not workspace:
            return None
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(workspace, field, value)
        await db.flush()
        return workspace

    async def delete(self, db: AsyncSession, workspace_id: int) -> bool:
        workspace = await self.get(db, workspace_id)
        if not workspace or workspace.is_default:
            return False
        self.vector_store.delete_workspace(workspace_id)
        await db.delete(workspace)
        return True
