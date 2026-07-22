"""Settings, style memory, chat, logs, and dashboard routes."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import Services, get_db, get_services
from app.schemas import (
    ChatMessageOut,
    ChatRequest,
    ChatResponse,
    DashboardStats,
    LogOut,
    SettingsOut,
    SettingsUpdate,
    StyleExampleCreate,
    StyleExampleOut,
    VocabularyCreate,
)

settings_router = APIRouter(prefix="/settings", tags=["settings"])
style_router = APIRouter(prefix="/style", tags=["style"])
chat_router = APIRouter(prefix="/chat", tags=["chat"])
logs_router = APIRouter(prefix="/logs", tags=["logs"])
dashboard_router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@settings_router.get("", response_model=SettingsOut)
async def get_settings(
    db: AsyncSession = Depends(get_db),
    services: Services = Depends(get_services),
):
    return await services.settings.get_settings(db)


@settings_router.put("", response_model=SettingsOut)
async def update_settings(
    data: SettingsUpdate,
    db: AsyncSession = Depends(get_db),
    services: Services = Depends(get_services),
):
    return await services.settings.update_settings(db, data)


@style_router.get("/examples", response_model=list[StyleExampleOut])
async def list_style_examples(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    services: Services = Depends(get_services),
):
    return await services.style.list_examples(db, limit=limit)


@style_router.post("/examples", response_model=StyleExampleOut)
async def add_style_example(
    data: StyleExampleCreate,
    db: AsyncSession = Depends(get_db),
    services: Services = Depends(get_services),
):
    return await services.style.add_example(
        db,
        content=data.content,
        category=data.category,
        notes=data.notes,
        greeting=data.greeting,
        sign_off=data.sign_off,
    )


@style_router.delete("/examples/{example_id}")
async def delete_style_example(
    example_id: int,
    db: AsyncSession = Depends(get_db),
    services: Services = Depends(get_services),
):
    ok = await services.style.delete_example(db, example_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Style example not found")
    return {"ok": True}


@style_router.post("/vocabulary")
async def add_vocabulary(
    data: VocabularyCreate,
    db: AsyncSession = Depends(get_db),
    services: Services = Depends(get_services),
):
    item = await services.style.add_vocabulary(
        db, data.term, data.preferred_form, data.notes
    )
    return {
        "id": item.id,
        "term": item.term,
        "preferred_form": item.preferred_form,
        "notes": item.notes,
    }


@style_router.get("/vocabulary")
async def list_vocabulary(
    db: AsyncSession = Depends(get_db),
    services: Services = Depends(get_services),
):
    items = await services.style.list_vocabulary(db)
    return [
        {
            "id": i.id,
            "term": i.term,
            "preferred_form": i.preferred_form,
            "notes": i.notes,
        }
        for i in items
    ]


@chat_router.post("", response_model=ChatResponse)
async def chat(
    data: ChatRequest,
    db: AsyncSession = Depends(get_db),
    services: Services = Depends(get_services),
):
    try:
        return await services.chat.chat(db, data)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@chat_router.get("/history", response_model=list[ChatMessageOut])
async def chat_history(
    workspace_id: Optional[int] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    services: Services = Depends(get_services),
):
    return await services.chat.history(db, workspace_id=workspace_id, limit=limit)


@logs_router.get("", response_model=list[LogOut])
async def list_logs(
    workspace_id: Optional[int] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    services: Services = Depends(get_services),
):
    return await services.log.list_logs(
        db, workspace_id=workspace_id, limit=limit, offset=offset
    )


@logs_router.get("/{log_id}", response_model=LogOut)
async def get_log(
    log_id: int,
    db: AsyncSession = Depends(get_db),
    services: Services = Depends(get_services),
):
    log = await services.log.get(db, log_id)
    if not log:
        raise HTTPException(status_code=404, detail="Log not found")
    return log


@dashboard_router.get("", response_model=DashboardStats)
async def dashboard(
    db: AsyncSession = Depends(get_db),
    services: Services = Depends(get_services),
):
    return await services.dashboard.get_stats(db)
