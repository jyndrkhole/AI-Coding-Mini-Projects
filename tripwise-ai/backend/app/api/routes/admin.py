from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, Field
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
    import hashlib

    cleaned = " ".join(text.split())
    digest = hashlib.sha256(cleaned.encode()).hexdigest()
    repo = KnowledgeRepository(db)
    if repo.by_hash(digest):
        raise HTTPException(status.HTTP_409_CONFLICT, detail={"code": "duplicate", "message": "That document is already in the notebook."})
    doc = repo.add(
        title=title or name,
        file_name=name,
        source="upload",
        document_type=suffix,
        destination=destination,
        ingestion_status="pending",
        content_hash=digest,
    )
    try:
        count = _store_upload(doc, cleaned)
        doc.ingestion_status = "ingested"
        doc.chunk_count = count
        doc.error_message = ""
    except Exception as exc:
        doc.ingestion_status = "error"
        doc.error_message = "Ingestion failed."
        repo.save(doc)
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail={"code": "ingest_failed", "message": "The file could not be indexed."}) from exc
    repo.save(doc)
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


def _store_upload(document: KnowledgeDocument, cleaned: str) -> int:
    from app.ai.chunking import chunk_text
    from app.ai.embeddings import get_embeddings
    from app.ai.vector_store import get_collection
    from app.core.config import get_settings

    settings = get_settings()
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    (settings.upload_dir / f"{document.id}.txt").write_text(cleaned, encoding="utf-8")
    chunks = chunk_text(cleaned, settings.chunk_size, settings.chunk_overlap)
    collection = get_collection()
    _delete_chunks(document)
    vectors = get_embeddings().embed_documents(chunks)
    collection.upsert(
        ids=[f"upload-{document.id}-{index}" for index in range(len(chunks))],
        embeddings=vectors,
        documents=chunks,
        metadatas=[
            {
                "document_id": str(document.id),
                "title": document.title,
                "destination": document.destination or "",
                "state": document.state or "",
                "country": document.country or "India",
                "topic": document.category or "upload",
                "travel_type": document.travel_type or "",
                "season": document.season or "",
                "source": "upload",
            }
            for _chunk in chunks
        ],
    )
    return len(chunks)


def _delete_chunks(document: KnowledgeDocument) -> None:
    from app.ai.vector_store import get_collection

    ids = [f"upload-{document.id}"]
    ids.extend(f"upload-{document.id}-{index}" for index in range(max(document.chunk_count, 1)))
    try:
        get_collection().delete(ids=ids)
    except Exception:
        pass


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
    from app.core.config import get_settings

    path = get_settings().upload_dir / f"{document.id}.txt"
    if not path.exists():
        document.ingestion_status = "error"
        document.error_message = "The original upload file is missing."
        KnowledgeRepository(db).save(document)
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail={"code": "missing_file", "message": "The original upload file is missing."})
    try:
        document.chunk_count = _store_upload(document, path.read_text(encoding="utf-8"))
        document.ingestion_status = "ingested"
        document.error_message = ""
    except Exception as exc:
        document.ingestion_status = "error"
        document.error_message = "Re-index failed."
        KnowledgeRepository(db).save(document)
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail={"code": "ingest_failed", "message": "The document could not be re-indexed."}) from exc
    KnowledgeRepository(db).save(document)
    return {"success": True, "data": serialize_document(document)}


@router.delete("/knowledge/{document_id}")
def delete_knowledge(document_id: int, db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    repo = KnowledgeRepository(db)
    document = repo.get(document_id)
    if document is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail={"code": "not_found", "message": "That document was not found."})
    try:
        if document.source == "tripwise-notebook":
            from app.ai.vector_store import get_collection

            get_collection().delete(ids=[document.content_hash])
        else:
            _delete_chunks(document)
    except Exception:
        pass
    repo.delete(document)
    return {"success": True, "data": {"deleted": True}}


class DestinationUpdate(BaseModel):
    description: str | None = None
    best_season: str | None = None
    family_fit: str | None = None
    couple_fit: str | None = None
    adventure_fit: str | None = None
    pros: str | None = None
    cons: str | None = None


class StayUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    price_per_night: float | None = Field(default=None, ge=0)


class AttractionUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    estimated_cost: float | None = Field(default=None, ge=0)


class TipUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    season: str | None = None
    category: str | None = None


class RoleUpdate(BaseModel):
    role: str


def _apply(row, fields: dict):
    for key, value in fields.items():
        if value is not None:
            setattr(row, key, value)
    return row


@router.get("/destinations")
def admin_destinations(db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    from app.database.repositories.destinations import DestinationRepository, serialize_detail

    repo = DestinationRepository(db)
    rows = []
    for destination in repo.list():
        loaded = repo.get(destination.id)
        if loaded:
            rows.append(serialize_detail(repo, loaded))
    return {"success": True, "data": rows}


@router.put("/destinations/{destination_id}")
def update_destination(destination_id: int, body: DestinationUpdate, db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    from app.database.models import Destination

    destination = db.get(Destination, destination_id)
    if destination is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail={"code": "not_found", "message": "That destination was not found."})
    _apply(destination, body.model_dump())
    db.commit()
    return {"success": True, "data": {"id": destination.id, "name": destination.name}}


@router.put("/accommodations/{stay_id}")
def update_stay(stay_id: int, body: StayUpdate, db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    from app.database.models import Accommodation

    stay = db.get(Accommodation, stay_id)
    if stay is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail={"code": "not_found", "message": "That stay was not found."})
    _apply(stay, body.model_dump())
    db.commit()
    return {"success": True, "data": {"id": stay.id, "price_per_night": float(stay.price_per_night), "price_label": "demonstration_estimate"}}


@router.put("/attractions/{attraction_id}")
def update_attraction(attraction_id: int, body: AttractionUpdate, db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    from app.database.models import Attraction

    item = db.get(Attraction, attraction_id)
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail={"code": "not_found", "message": "That attraction was not found."})
    _apply(item, body.model_dump())
    db.commit()
    return {"success": True, "data": {"id": item.id, "estimated_cost": float(item.estimated_cost or 0)}}


@router.put("/tips/{tip_id}")
def update_tip(tip_id: int, body: TipUpdate, db: Session = Depends(get_db), _admin: User = Depends(require_admin)):
    from app.database.models import TravelTip

    tip = db.get(TravelTip, tip_id)
    if tip is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail={"code": "not_found", "message": "That tip was not found."})
    _apply(tip, body.model_dump())
    db.commit()
    return {"success": True, "data": {"id": tip.id, "title": tip.title}}


@router.put("/users/{user_id}/role")
def update_role(user_id: int, body: RoleUpdate, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    if body.role not in {"user", "admin"}:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail={"code": "invalid", "message": "Role must be user or admin."})
    if user_id == admin.id and body.role != "admin":
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail={"code": "invalid", "message": "You cannot remove your own admin role."})
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail={"code": "not_found", "message": "That user was not found."})
    target.role = body.role
    db.commit()
    return {"success": True, "data": user_public(target)}
