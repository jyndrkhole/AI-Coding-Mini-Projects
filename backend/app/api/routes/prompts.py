"""Prompt library routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import Services, get_db, get_services
from app.schemas import PromptCreate, PromptOut, PromptUpdate

router = APIRouter(prefix="/prompts", tags=["prompts"])


@router.get("", response_model=list[PromptOut])
async def list_prompts(
    db: AsyncSession = Depends(get_db),
    services: Services = Depends(get_services),
):
    return await services.prompt.list_prompts(db)


@router.post("", response_model=PromptOut)
async def create_prompt(
    data: PromptCreate,
    db: AsyncSession = Depends(get_db),
    services: Services = Depends(get_services),
):
    return await services.prompt.create(db, data)


@router.patch("/{prompt_id}", response_model=PromptOut)
async def update_prompt(
    prompt_id: int,
    data: PromptUpdate,
    db: AsyncSession = Depends(get_db),
    services: Services = Depends(get_services),
):
    prompt = await services.prompt.update(db, prompt_id, data)
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return prompt


@router.delete("/{prompt_id}")
async def delete_prompt(
    prompt_id: int,
    db: AsyncSession = Depends(get_db),
    services: Services = Depends(get_services),
):
    ok = await services.prompt.delete(db, prompt_id)
    if not ok:
        raise HTTPException(
            status_code=400, detail="Cannot delete prompt (not found or built-in)"
        )
    return {"ok": True}
