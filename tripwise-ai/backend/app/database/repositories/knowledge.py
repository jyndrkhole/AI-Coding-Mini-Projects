from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models import KnowledgeDocument


class KnowledgeRepository:
    def __init__(self, db: Session):
        self.db = db

    def list(self) -> list[KnowledgeDocument]:
        return list(self.db.scalars(select(KnowledgeDocument).order_by(KnowledgeDocument.created_at.desc())))

    def get(self, document_id: int) -> KnowledgeDocument | None:
        return self.db.get(KnowledgeDocument, document_id)

    def by_hash(self, content_hash: str) -> KnowledgeDocument | None:
        return self.db.scalars(
            select(KnowledgeDocument).where(KnowledgeDocument.content_hash == content_hash)
        ).first()

    def add(self, **fields) -> KnowledgeDocument:
        document = KnowledgeDocument(**fields)
        self.db.add(document)
        self.db.commit()
        self.db.refresh(document)
        return document

    def save(self, document: KnowledgeDocument) -> KnowledgeDocument:
        self.db.commit()
        self.db.refresh(document)
        return document

    def delete(self, document: KnowledgeDocument) -> None:
        self.db.delete(document)
        self.db.commit()


def serialize_document(document: KnowledgeDocument) -> dict:
    return {
        "id": document.id,
        "title": document.title,
        "file_name": document.file_name,
        "source": document.source,
        "document_type": document.document_type,
        "destination": document.destination,
        "state": document.state,
        "country": document.country,
        "category": document.category,
        "travel_type": document.travel_type,
        "season": document.season,
        "source_url": document.source_url,
        "ingestion_status": document.ingestion_status,
        "error_message": document.error_message,
        "chunk_count": document.chunk_count,
        "created_at": document.created_at.isoformat() if document.created_at else None,
        "updated_at": document.updated_at.isoformat() if document.updated_at else None,
    }
