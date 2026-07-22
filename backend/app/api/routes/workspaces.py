"""Workspace management routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import Services, get_db, get_services
from app.schemas import WorkspaceCreate, WorkspaceOut, WorkspaceUpdate

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.get("", response_model=list[WorkspaceOut])
async def list_workspaces(
    db: AsyncSession = Depends(get_db),
    services: Services = Depends(get_services),
):
    await services.workspace.ensure_default(db)
    return await services.workspace.list_workspaces(db)


@router.post("", response_model=WorkspaceOut)
async def create_workspace(
    data: WorkspaceCreate,
    db: AsyncSession = Depends(get_db),
    services: Services = Depends(get_services),
):
    workspace = await services.workspace.create(db, data)
    return WorkspaceOut(
        id=workspace.id,
        name=workspace.name,
        description=workspace.description,
        color=workspace.color,
        is_default=workspace.is_default,
        created_at=workspace.created_at,
        document_count=0,
        email_count=0,
    )


@router.patch("/{workspace_id}", response_model=WorkspaceOut)
async def update_workspace(
    workspace_id: int,
    data: WorkspaceUpdate,
    db: AsyncSession = Depends(get_db),
    services: Services = Depends(get_services),
):
    workspace = await services.workspace.update(db, workspace_id, data)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    items = await services.workspace.list_workspaces(db)
    for item in items:
        if item.id == workspace_id:
            return item
    raise HTTPException(status_code=404, detail="Workspace not found")


@router.delete("/{workspace_id}")
async def delete_workspace(
    workspace_id: int,
    db: AsyncSession = Depends(get_db),
    services: Services = Depends(get_services),
):
    ok = await services.workspace.delete(db, workspace_id)
    if not ok:
        raise HTTPException(
            status_code=400, detail="Cannot delete workspace (not found or default)"
        )
    return {"ok": True}
