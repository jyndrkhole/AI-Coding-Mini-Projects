"""Context retrieval helpers for email generation."""

from typing import Optional

from app.config import get_settings
from app.rag.vector_store import RetrievedChunk, VectorStore


CATEGORY_MAP = {
    "architecture": ["architecture", "design"],
    "meeting_notes": ["meeting_notes", "notes", "meeting"],
    "previous_emails": ["email", "previous_emails", "sent_email"],
    "project_documents": ["project", "requirements", "proposal", "general"],
    "chatgpt_knowledge": ["chatgpt_history"],
    "personal_notes": ["notes", "personal", "sop"],
}


class Retriever:
    def __init__(self, vector_store: Optional[VectorStore] = None):
        self.vector_store = vector_store or VectorStore()
        self.settings = get_settings()

    async def retrieve(
        self,
        workspace_id: int,
        query: str,
        context_sources: Optional[list[str]] = None,
        top_k: Optional[int] = None,
    ) -> list[RetrievedChunk]:
        categories: list[str] = []
        if context_sources:
            for source in context_sources:
                categories.extend(CATEGORY_MAP.get(source, [source]))

        # Chroma where filters with $in work for metadata
        where = None
        if categories:
            unique = list(set(categories))
            where = {"category": {"$in": unique}} if len(unique) > 1 else {"category": unique[0]}

        try:
            return await self.vector_store.search(
                workspace_id, query, top_k=top_k or self.settings.retrieval_top_k, where=where
            )
        except Exception:
            # If filtered search fails (e.g. no matching metadata), fall back
            return await self.vector_store.search(
                workspace_id, query, top_k=top_k or self.settings.retrieval_top_k
            )

    def format_context(self, chunks: list[RetrievedChunk]) -> str:
        if not chunks:
            return ""
        parts = []
        for i, chunk in enumerate(chunks, 1):
            source = chunk.metadata.get("filename", "unknown")
            category = chunk.metadata.get("category", "general")
            parts.append(
                f"[Source {i} | {source} | {category} | score={chunk.score:.2f}]\n{chunk.content}"
            )
        return "\n\n---\n\n".join(parts)
