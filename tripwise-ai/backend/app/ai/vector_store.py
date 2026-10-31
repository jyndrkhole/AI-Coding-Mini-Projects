"""Persistent Chroma collection. This store holds travel notes, never prices."""

import chromadb

from app.core.config import get_settings

_client = None


def get_client():
    global _client
    if _client is None:
        settings = get_settings()
        settings.chroma_dir.mkdir(parents=True, exist_ok=True)
        _client = chromadb.PersistentClient(path=str(settings.chroma_dir))
    return _client


def get_collection():
    settings = get_settings()
    return get_client().get_or_create_collection(
        name=settings.chroma_collection,
        metadata={"hnsw:space": "cosine"},
    )


def collection_count() -> int:
    try:
        return int(get_collection().count())
    except Exception:
        return 0
