"""Email compose, reply, rewrite, and thread analysis routes."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import Services, get_db, get_services
from app.schemas import (
    ComposeRequest,
    EmailGenerateResponse,
    EmailOut,
    EmailSaveFinalRequest,
    ReplyRequest,
    RewriteRequest,
    ThreadAnalysis,
    ThreadAnalyzeRequest,
)

router = APIRouter(prefix="/emails", tags=["emails"])


@router.post("/compose", response_model=EmailGenerateResponse)
async def compose_email(
    data: ComposeRequest,
    db: AsyncSession = Depends(get_db),
    services: Services = Depends(get_services),
):
    try:
        return await services.email.compose(db, data)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/reply", response_model=EmailGenerateResponse)
async def reply_email(
    data: ReplyRequest,
    db: AsyncSession = Depends(get_db),
    services: Services = Depends(get_services),
):
    try:
        return await services.email.reply(db, data)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/rewrite", response_model=EmailGenerateResponse)
async def rewrite_email(
    data: RewriteRequest,
    db: AsyncSession = Depends(get_db),
    services: Services = Depends(get_services),
):
    try:
        return await services.email.rewrite(db, data)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/analyze-thread", response_model=ThreadAnalysis)
async def analyze_thread(
    data: ThreadAnalyzeRequest,
    db: AsyncSession = Depends(get_db),
    services: Services = Depends(get_services),
):
    try:
        return await services.email.analyze_thread(db, data)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/{email_id}/save-final", response_model=EmailOut)
async def save_final(
    email_id: int,
    data: EmailSaveFinalRequest,
    db: AsyncSession = Depends(get_db),
    services: Services = Depends(get_services),
):
    email = await services.email.save_final(
        db, email_id, data.final_text, data.use_as_style_example
    )
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")
    return email


@router.get("", response_model=list[EmailOut])
async def list_emails(
    workspace_id: Optional[int] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    services: Services = Depends(get_services),
):
    return await services.email.list_emails(db, workspace_id=workspace_id, limit=limit)
