"""Prompt library service."""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import PromptTemplate
from app.prompts.templates import BUILTIN_PROMPTS
from app.schemas import PromptCreate, PromptUpdate


class PromptService:
    async def seed_builtins(self, db: AsyncSession) -> None:
        result = await db.execute(
            select(PromptTemplate).where(PromptTemplate.is_builtin.is_(True))
        )
        existing = {p.name for p in result.scalars().all()}
        for item in BUILTIN_PROMPTS:
            if item["name"] in existing:
                continue
            db.add(
                PromptTemplate(
                    name=item["name"],
                    category=item["category"],
                    description=item["description"],
                    template=item["template"],
                    variables=item["variables"],
                    is_builtin=True,
                )
            )
        await db.flush()

    async def list_prompts(self, db: AsyncSession) -> list[PromptTemplate]:
        result = await db.execute(
            select(PromptTemplate).order_by(
                PromptTemplate.is_builtin.desc(), PromptTemplate.name.asc()
            )
        )
        return list(result.scalars().all())

    async def get(self, db: AsyncSession, prompt_id: int) -> Optional[PromptTemplate]:
        result = await db.execute(
            select(PromptTemplate).where(PromptTemplate.id == prompt_id)
        )
        return result.scalar_one_or_none()

    async def create(self, db: AsyncSession, data: PromptCreate) -> PromptTemplate:
        prompt = PromptTemplate(
            name=data.name,
            category=data.category,
            description=data.description,
            template=data.template,
            variables=data.variables,
            is_builtin=False,
        )
        db.add(prompt)
        await db.flush()
        return prompt

    async def update(
        self, db: AsyncSession, prompt_id: int, data: PromptUpdate
    ) -> Optional[PromptTemplate]:
        prompt = await self.get(db, prompt_id)
        if not prompt:
            return None
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(prompt, field, value)
        await db.flush()
        return prompt

    async def delete(self, db: AsyncSession, prompt_id: int) -> bool:
        prompt = await self.get(db, prompt_id)
        if not prompt or prompt.is_builtin:
            return False
        await db.delete(prompt)
        return True
