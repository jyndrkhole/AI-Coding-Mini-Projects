"""Knowledge base and search services."""

from pathlib import Path
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Document
from app.rag.ingest import IngestService
from app.rag.retriever import Retriever
from app.rag.vector_store import VectorStore
from app.schemas import SearchRequest, SearchResponse, SearchResult


class KnowledgeService:
    def __init__(self):
        self.ingest = IngestService()
        self.vector_store = VectorStore()
        self.retriever = Retriever(self.vector_store)

    async def list_documents(
        self, db: AsyncSession, workspace_id: Optional[int] = None
    ) -> list[Document]:
        query = select(Document).order_by(Document.created_at.desc())
        if workspace_id is not None:
            query = query.where(Document.workspace_id == workspace_id)
        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_document(self, db: AsyncSession, document_id: int) -> Optional[Document]:
        result = await db.execute(select(Document).where(Document.id == document_id))
        return result.scalar_one_or_none()

    async def upload_file(
        self,
        db: AsyncSession,
        workspace_id: int,
        file_path: Path,
        original_name: str,
        category: str = "general",
    ) -> Document:
        return await self.ingest.ingest_file(
            db, workspace_id, file_path, original_name, category=category
        )

    async def ingest_text(
        self,
        db: AsyncSession,
        workspace_id: int,
        title: str,
        content: str,
        category: str = "notes",
    ) -> Document:
        return await self.ingest.ingest_text(
            db, workspace_id, content, title, category=category
        )

    async def import_chatgpt(
        self,
        db: AsyncSession,
        workspace_id: int,
        content: str,
        title: str = "ChatGPT Conversation",
    ) -> Document:
        return await self.ingest.ingest_chatgpt_export(
            db, workspace_id, content, title=title
        )

    async def delete_document(self, db: AsyncSession, document_id: int) -> bool:
        doc = await self.get_document(db, document_id)
        if not doc:
            return False
        self.vector_store.delete_document(doc.workspace_id, doc.id)
        path = Path(doc.file_path)
        if path.exists():
            path.unlink(missing_ok=True)
        await db.delete(doc)
        return True

    async def search(self, data: SearchRequest) -> SearchResponse:
        chunks = await self.retriever.retrieve(
            data.workspace_id,
            data.query,
            context_sources=data.context_sources or None,
            top_k=data.top_k,
        )
        return SearchResponse(
            query=data.query,
            results=[
                SearchResult(
                    id=c.id,
                    content=c.content,
                    score=c.score,
                    metadata=c.metadata,
                )
                for c in chunks
            ],
        )
