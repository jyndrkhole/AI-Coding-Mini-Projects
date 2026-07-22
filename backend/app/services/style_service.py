"""Writing style memory service."""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import StyleExample, VocabularyPreference


class StyleService:
    async def add_example(
        self,
        db: AsyncSession,
        content: str,
        category: str = "sent_email",
        notes: Optional[str] = None,
        greeting: Optional[str] = None,
        sign_off: Optional[str] = None,
        email_id: Optional[int] = None,
    ) -> StyleExample:
        example = StyleExample(
            email_id=email_id,
            content=content,
            category=category,
            notes=notes,
            greeting=greeting,
            sign_off=sign_off,
        )
        db.add(example)
        await db.flush()
        return example

    async def list_examples(
        self, db: AsyncSession, limit: int = 20
    ) -> list[StyleExample]:
        result = await db.execute(
            select(StyleExample)
            .order_by(StyleExample.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def delete_example(self, db: AsyncSession, example_id: int) -> bool:
        result = await db.execute(
            select(StyleExample).where(StyleExample.id == example_id)
        )
        example = result.scalar_one_or_none()
        if not example:
            return False
        await db.delete(example)
        return True

    async def build_style_context(self, db: AsyncSession, limit: int = 5) -> str:
        examples = await self.list_examples(db, limit=limit)
        vocab = await self.list_vocabulary(db)

        parts: list[str] = []
        if examples:
            parts.append("### Sent / Preferred Email Examples")
            for i, ex in enumerate(examples, 1):
                meta = []
                if ex.greeting:
                    meta.append(f"greeting: {ex.greeting}")
                if ex.sign_off:
                    meta.append(f"sign-off: {ex.sign_off}")
                header = f"Example {i}"
                if meta:
                    header += f" ({', '.join(meta)})"
                parts.append(f"{header}:\n{ex.content}")

        if vocab:
            parts.append("### Vocabulary Preferences")
            for v in vocab:
                parts.append(f"- Prefer '{v.preferred_form}' instead of '{v.term}'")

        return "\n\n".join(parts)

    async def add_vocabulary(
        self,
        db: AsyncSession,
        term: str,
        preferred_form: str,
        notes: Optional[str] = None,
    ) -> VocabularyPreference:
        item = VocabularyPreference(
            term=term, preferred_form=preferred_form, notes=notes
        )
        db.add(item)
        await db.flush()
        return item

    async def list_vocabulary(self, db: AsyncSession) -> list[VocabularyPreference]:
        result = await db.execute(
            select(VocabularyPreference).order_by(VocabularyPreference.created_at.desc())
        )
        return list(result.scalars().all())
