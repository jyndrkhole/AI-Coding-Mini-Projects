"""ChromaDB vector store wrapper with workspace isolation."""

from dataclasses import dataclass
from typing import Any, Optional
from uuid import uuid4

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.config import get_settings
from app.rag.embeddings import BaseEmbeddingProvider, get_embedding_provider


@dataclass
class RetrievedChunk:
    id: str
    content: str
    metadata: dict[str, Any]
    score: float


class VectorStore:
    """Per-workspace Chroma collections for RAG isolation."""

    def __init__(self, embedding_provider: Optional[BaseEmbeddingProvider] = None):
        settings = get_settings()
        settings.vector_db_path.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(
            path=str(settings.vector_db_path),
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self.embeddings = embedding_provider or get_embedding_provider()
        self.top_k = settings.retrieval_top_k

    def _collection_name(self, workspace_id: int) -> str:
        return f"workspace_{workspace_id}"

    def get_or_create_collection(self, workspace_id: int):
        return self.client.get_or_create_collection(
            name=self._collection_name(workspace_id),
            metadata={"hnsw:space": "cosine"},
        )

    async def add_chunks(
        self,
        workspace_id: int,
        texts: list[str],
        metadatas: list[dict[str, Any]],
        ids: Optional[list[str]] = None,
    ) -> list[str]:
        if not texts:
            return []
        collection = self.get_or_create_collection(workspace_id)
        ids = ids or [str(uuid4()) for _ in texts]
        embeddings = await self.embeddings.embed_documents(texts)
        collection.add(
            ids=ids,
            documents=texts,
            embeddings=embeddings,
            metadatas=metadatas,
        )
        return ids

    async def search(
        self,
        workspace_id: int,
        query: str,
        top_k: Optional[int] = None,
        where: Optional[dict[str, Any]] = None,
    ) -> list[RetrievedChunk]:
        collection = self.get_or_create_collection(workspace_id)
        if collection.count() == 0:
            return []

        query_embedding = await self.embeddings.embed_query(query)
        kwargs: dict[str, Any] = {
            "query_embeddings": [query_embedding],
            "n_results": min(top_k or self.top_k, collection.count()),
        }
        if where:
            kwargs["where"] = where

        results = collection.query(**kwargs)
        chunks: list[RetrievedChunk] = []
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]
        ids = results.get("ids", [[]])[0]

        for doc_id, doc, meta, dist in zip(ids, documents, metadatas, distances):
            score = 1.0 - float(dist) if dist is not None else 0.0
            chunks.append(
                RetrievedChunk(
                    id=doc_id,
                    content=doc,
                    metadata=meta or {},
                    score=score,
                )
            )
        return chunks

    def delete_document(self, workspace_id: int, document_id: int) -> None:
        collection = self.get_or_create_collection(workspace_id)
        try:
            collection.delete(where={"document_id": document_id})
        except Exception:
            # Fallback: delete by scanning if where filter unsupported
            existing = collection.get(where={"document_id": document_id})
            if existing and existing.get("ids"):
                collection.delete(ids=existing["ids"])

    def delete_workspace(self, workspace_id: int) -> None:
        name = self._collection_name(workspace_id)
        try:
            self.client.delete_collection(name)
        except Exception:
            pass

    def count(self, workspace_id: int) -> int:
        return self.get_or_create_collection(workspace_id).count()
