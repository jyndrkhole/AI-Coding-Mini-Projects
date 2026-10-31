from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ai.vector_store import collection_count
from app.api.deps import require_admin
from app.database.connection import get_db
from app.database.models import ChatSession, KnowledgeDocument, Trip, User
from app.database.repositories.accounts import StatsRepository, UserRepository, user_public
from app.database.repositories.knowledge import KnowledgeRepository, serialize_document

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    stats = StatsRepository(db)
    recent_trips = list(db.scalars(select(Trip).order_by(Trip.created_at.desc()).limit(6)))
    recent_chats = list(db.scalars(select(ChatSession).order_by(ChatSession.updated_at.desc()).limit(6)))
    documents = KnowledgeRepository(db).list()
    return {
        "success": True,
        "data": {
            **stats.counts(),
            "chroma_documents": collection_count(),
            "ingestion_errors": [
                serialize_document(doc) for doc in documents if doc.ingestion_status == "error"
            ],
            "recent_trips": [
                {"id": trip.id, "title": trip.title, "user_id": trip.user_id} for trip in recent_trips
            ],
            "recent_sessions": [
                {"id": item.id, "title": item.session_title, "user_id": item.user_id} for item in recent_chats
            ],
        },
    }


@router.get("/knowledge")
def list_knowledge(db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    return {"success": True, "data": [serialize_document(doc) for doc in KnowledgeRepository(db).list()]}


@router.get("/users")
def list_users(db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    return {"success": True, "data": [user_public(user) for user in UserRepository(db).list_users()]}


@router.post("/knowledge/upload")
async def upload_knowledge(
    file: UploadFile = File(...),
    title: str = Form(""),
    destination: str = Form(""),
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    name = file.filename or "note.txt"
    suffix = name.rsplit(".", 1)[-1].lower()
    if suffix not in {"txt", "md", "pdf", "docx"}:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail={"code": "bad_file", "message": "Upload a txt, md, pdf, or docx file."})
    raw = await file.read()
    from app.core.config import get_settings

    if len(raw) > get_settings().upload_max_bytes:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail={"code": "too_large", "message": "That file is larger than the upload limit."})
    text = _extract(suffix, raw)
    if not text.strip():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail={"code": "empty", "message": "No text could be read from that file."})
    doc = KnowledgeRepository(db).add(
        title=title or name,
        file_name=name,
        source="upload",
        document_type=suffix,
        destination=destination,
        ingestion_status="pending",
        content_hash="",
    )
    try:
        _store_upload(doc, text)
        doc.ingestion_status = "ingested"
        doc.chunk_count = 1
        doc.error_message = ""
    except Exception as exc:
        doc.ingestion_status = "error"
        doc.error_message = "Ingestion failed."
        KnowledgeRepository(db).save(doc)
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail={"code": "ingest_failed", "message": "The file could not be indexed."}) from exc
    KnowledgeRepository(db).save(doc)
    return {"success": True, "data": serialize_document(doc)}


def _extract(suffix: str, raw: bytes) -> str:
    if suffix in {"txt", "md"}:
        return raw.decode("utf-8", errors="ignore")
    if suffix == "pdf":
        from pypdf import PdfReader
        import io

        reader = PdfReader(io.BytesIO(raw))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    from io import BytesIO

    import docx

    document = docx.Document(BytesIO(raw))
    return "\n".join(paragraph.text for paragraph in document.paragraphs)


def _store_upload(document: KnowledgeDocument, text: str) -> None:
    import hashlib

    from app.ai.embeddings import get_embeddings
    from app.ai.vector_store import get_collection

    cleaned = " ".join(text.split())
    digest = hashlib.sha256(cleaned.encode()).hexdigest()
    document.content_hash = digest
    collection = get_collection()
    vector = get_embeddings().embed_documents([cleaned])
    collection.upsert(
        ids=[f"upload-{document.id}"],
        embeddings=vector,
        documents=[cleaned[:4000]],
        metadatas=[{"topic": "upload", "destination": document.destination or "", "travel_type": "", "season": ""}],
    )


@router.post("/knowledge/{document_id}/reindex")
def reindex(document_id: int, db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    from app.ai.ingestion import ingest_notebook

    document = KnowledgeRepository(db).get(document_id)
    if document is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail={"code": "not_found", "message": "That document was not found."})
    if document.source == "tripwise-notebook":
        ingest_notebook()
        document.ingestion_status = "ingested"
        document.error_message = ""
        KnowledgeRepository(db).save(document)
    return {"success": True, "data": serialize_document(document)}


@router.delete("/knowledge/{document_id}")
def delete_knowledge(document_id: int, db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    repo = KnowledgeRepository(db)
    document = repo.get(document_id)
    if document is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail={"code": "not_found", "message": "That document was not found."})
    try:
        from app.ai.vector_store import get_collection

        get_collection().delete(ids=[document.content_hash if document.source == "tripwise-notebook" else f"upload-{document.id}"])
    except Exception:
        pass
    repo.delete(document)
    return {"success": True, "data": {"deleted": True}}
