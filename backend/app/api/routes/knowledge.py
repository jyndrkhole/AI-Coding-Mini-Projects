"""Knowledge base and search routes."""

import tempfile
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import Services, get_db, get_services
from app.schemas import (
    ChatGPTImportRequest,
    DocumentOut,
    SearchRequest,
    SearchResponse,
    TextIngestRequest,
)

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.get("/documents", response_model=list[DocumentOut])
async def list_documents(
    workspace_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
    services: Services = Depends(get_services),
):
    return await services.knowledge.list_documents(db, workspace_id=workspace_id)


@router.post("/upload", response_model=DocumentOut)
async def upload_document(
    workspace_id: int = Form(...),
    category: str = Form("general"),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    services: Services = Depends(get_services),
):
    suffix = Path(file.filename or "upload.txt").suffix
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = Path(tmp.name)
        doc = await services.knowledge.upload_file(
            db,
            workspace_id,
            tmp_path,
            original_name=file.filename or "upload",
            category=category,
        )
        tmp_path.unlink(missing_ok=True)
        return doc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/text", response_model=DocumentOut)
async def ingest_text(
    data: TextIngestRequest,
    db: AsyncSession = Depends(get_db),
    services: Services = Depends(get_services),
):
    try:
        return await services.knowledge.ingest_text(
            db, data.workspace_id, data.title, data.content, data.category
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/import-chatgpt", response_model=DocumentOut)
async def import_chatgpt(
    data: ChatGPTImportRequest,
    db: AsyncSession = Depends(get_db),
    services: Services = Depends(get_services),
):
    try:
        return await services.knowledge.import_chatgpt(
            db, data.workspace_id, data.content, data.title
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: int,
    db: AsyncSession = Depends(get_db),
    services: Services = Depends(get_services),
):
    ok = await services.knowledge.delete_document(db, document_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"ok": True}


@router.post("/search", response_model=SearchResponse)
async def search_knowledge(
    data: SearchRequest,
    services: Services = Depends(get_services),
):
    return await services.knowledge.search(data)
