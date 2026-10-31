"""Semantic retrieval. Chroma distance in cosine space is converted back to similarity."""

from app.ai.embeddings import get_embeddings
from app.ai.vector_store import get_collection
from app.core.config import get_settings


def similarity_from_distance(distance: float) -> float:
    return 1.0 - float(distance)


def filter_hits(ids, documents, metadatas, distances, threshold: float) -> list[dict]:
    kept = []
    for doc_id, document, metadata, distance in zip(ids, documents, metadatas, distances):
        similarity = similarity_from_distance(distance)
        if similarity >= threshold:
            kept.append(
                {
                    "id": doc_id,
                    "text": document,
                    "metadata": metadata or {},
                    "similarity": round(similarity, 4),
                }
            )
    return kept


def retrieve(query: str, k: int | None = None, where: dict | None = None) -> list[dict]:
    settings = get_settings()
    collection = get_collection()
    count = collection.count()
    if count == 0:
        return []
    n_results = min(k or settings.retrieval_k, count)
    query_vector = get_embeddings().embed_query(query)
    kwargs = {
        "query_embeddings": [query_vector],
        "n_results": n_results,
        "include": ["documents", "metadatas", "distances"],
    }
    if where:
        kwargs["where"] = where
    try:
        result = collection.query(**kwargs)
    except Exception:
        if where:
            return retrieve(query, k=k, where=None)
        return []
    docs = result.get("documents") or [[]]
    if not docs or not docs[0]:
        return []
    return filter_hits(
        (result.get("ids") or [[]])[0],
        docs[0],
        (result.get("metadatas") or [[]])[0],
        (result.get("distances") or [[]])[0],
        settings.similarity_threshold,
    )


def retrieve_context(query: str, k: int | None = None) -> str:
    hits = retrieve(query, k=k)
    if not hits:
        count = get_collection().count()
        if count == 0:
            return "No travel notes have been ingested into the notebook yet."
        return "No notebook passage scored above the similarity threshold. Say that the notebook does not cover this."
    return "\n".join(f"- {hit['text']}" for hit in hits)
