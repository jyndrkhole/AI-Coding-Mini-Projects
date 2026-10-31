"""Write the travel notebook into persistent Chroma. Re-running updates the same ids."""

from app.ai.embeddings import get_embeddings
from app.ai.notebook import NOTEBOOK
from app.ai.vector_store import get_collection
from app.database.connection import SessionLocal, init_db
from app.database.repositories.knowledge import KnowledgeRepository


def ingest_notebook() -> int:
    init_db()
    ids = [item[0] for item in NOTEBOOK]
    documents = [item[1] for item in NOTEBOOK]
    metadatas = []
    for _doc_id, _text, meta in NOTEBOOK:
        metadatas.append({key: value for key, value in meta.items()})
    vectors = get_embeddings().embed_documents(documents)
    collection = get_collection()
    collection.upsert(ids=ids, embeddings=vectors, documents=documents, metadatas=metadatas)

    db = SessionLocal()
    try:
        repo = KnowledgeRepository(db)
        for doc_id, text, meta in NOTEBOOK:
            existing = repo.by_hash(doc_id)
            fields = dict(
                title=doc_id,
                file_name=f"{doc_id}.md",
                source="tripwise-notebook",
                document_type="md",
                destination=meta.get("destination", ""),
                category=meta.get("topic", "guide"),
                travel_type=meta.get("travel_type", ""),
                season=meta.get("season", ""),
                ingestion_status="ingested",
                error_message="",
                content_hash=doc_id,
                chunk_count=1,
            )
            if existing:
                for key, value in fields.items():
                    setattr(existing, key, value)
                repo.save(existing)
            else:
                repo.add(**fields)
    finally:
        db.close()
    return len(ids)
