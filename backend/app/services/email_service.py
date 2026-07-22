"""Email compose, reply, rewrite, and thread analysis services."""

import time
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import EmailRecord, PromptTemplate
from app.llm.factory import get_llm_provider
from app.prompts.templates import (
    CTO_SYSTEM_PROMPT,
    build_compose_prompt,
    build_reply_prompt,
    build_rewrite_prompt,
    build_suggestions_prompt,
    build_thread_analysis_prompt,
)
from app.rag.retriever import Retriever
from app.schemas import (
    ComposeRequest,
    EmailGenerateResponse,
    EmailSuggestions,
    ReplyRequest,
    RewriteRequest,
    ThreadAnalysis,
    ThreadAnalyzeRequest,
)
from app.services.log_service import LogService
from app.services.style_service import StyleService
from app.services.workspace_service import WorkspaceService
from app.utils.json_utils import extract_json


class EmailService:
    def __init__(self):
        self.retriever = Retriever()
        self.style_service = StyleService()
        self.log_service = LogService()
        self.workspace_service = WorkspaceService()

    async def _resolve_workspace(
        self, db: AsyncSession, workspace_id: Optional[int]
    ) -> int:
        if workspace_id:
            return workspace_id
        default = await self.workspace_service.ensure_default(db)
        return default.id

    async def _get_context(
        self,
        workspace_id: int,
        query: str,
        context_sources: list[str],
        use_kb: bool,
    ) -> str:
        if not use_kb:
            return ""
        chunks = await self.retriever.retrieve(
            workspace_id, query, context_sources=context_sources or None
        )
        return self.retriever.format_context(chunks)

    async def _generate_suggestions(self, db: AsyncSession, email_text: str) -> EmailSuggestions:
        try:
            llm = await get_llm_provider(db)
            prompt = build_suggestions_prompt(email_text)
            response = await llm.generate_text(
                prompt, system=CTO_SYSTEM_PROMPT, temperature=0.2
            )
            data = extract_json(response.content)
            return EmailSuggestions(
                client_concerns=data.get("client_concerns", []),
                missing_technical_points=data.get("missing_technical_points", []),
                ambiguous_statements=data.get("ambiguous_statements", []),
                risk_analysis=data.get("risk_analysis", []),
                confidence_score=float(data.get("confidence_score", 0) or 0),
                alternative_wording=data.get("alternative_wording", []),
            )
        except Exception:
            return EmailSuggestions()

    async def analyze_thread(
        self, db: AsyncSession, data: ThreadAnalyzeRequest
    ) -> ThreadAnalysis:
        llm = await get_llm_provider(db)
        prompt = build_thread_analysis_prompt(data.thread)
        started = time.perf_counter()
        response = await llm.generate_text(prompt, system=CTO_SYSTEM_PROMPT, temperature=0.1)
        latency = int((time.perf_counter() - started) * 1000)
        parsed = extract_json(response.content)

        await self.log_service.create(
            db,
            action="thread_analyze",
            input_text=data.thread[:5000],
            prompt=prompt,
            llm_response=response.content,
            provider=response.provider,
            model=response.model,
            workspace_id=data.workspace_id,
            tokens_used=response.tokens_used,
            latency_ms=latency,
        )

        return ThreadAnalysis(
            summary=parsed.get("summary", ""),
            key_decisions=parsed.get("key_decisions", []),
            pending_questions=parsed.get("pending_questions", []),
            blockers=parsed.get("blockers", []),
            commitments=parsed.get("commitments", []),
            risks=parsed.get("risks", []),
            next_actions=parsed.get("next_actions", []),
            stakeholders=parsed.get("stakeholders", []),
        )

    async def compose(
        self, db: AsyncSession, data: ComposeRequest
    ) -> EmailGenerateResponse:
        workspace_id = await self._resolve_workspace(db, data.workspace_id)
        style_examples = ""
        if data.use_style_memory:
            style_examples = await self.style_service.build_style_context(db)

        notes = data.rough_notes
        if data.prompt_template_id:
            result = await db.execute(
                select(PromptTemplate).where(PromptTemplate.id == data.prompt_template_id)
            )
            template = result.scalar_one_or_none()
            if template:
                notes = template.template.replace("{{input}}", data.rough_notes)
                template.usage_count += 1

        context = await self._get_context(
            workspace_id,
            data.rough_notes,
            data.context_sources,
            data.use_knowledge_base,
        )
        prompt = build_compose_prompt(
            notes,
            context=context,
            style_examples=style_examples,
            subject=data.subject,
            extra_instructions=data.extra_instructions,
        )

        llm = await get_llm_provider(db)
        started = time.perf_counter()
        response = await llm.generate_text(prompt, system=CTO_SYSTEM_PROMPT)
        latency = int((time.perf_counter() - started) * 1000)

        suggestions = await self._generate_suggestions(db, response.content)

        email = EmailRecord(
            workspace_id=workspace_id,
            mode="compose",
            subject=data.subject,
            input_text=data.rough_notes,
            generated_text=response.content,
            context_sources=data.context_sources,
            suggestions=suggestions.model_dump(),
        )
        db.add(email)
        await db.flush()

        await self.log_service.create(
            db,
            action="compose",
            input_text=data.rough_notes,
            prompt=prompt,
            llm_response=response.content,
            provider=response.provider,
            model=response.model,
            workspace_id=workspace_id,
            context_used=context or None,
            temperature=llm.config.temperature,
            tokens_used=response.tokens_used,
            latency_ms=latency,
            metadata={"email_id": email.id},
        )

        return EmailGenerateResponse(
            id=email.id,
            generated_text=response.content,
            subject=data.subject,
            suggestions=suggestions,
            context_used=context or None,
            provider=response.provider,
            model=response.model,
        )

    async def reply(
        self, db: AsyncSession, data: ReplyRequest
    ) -> EmailGenerateResponse:
        workspace_id = await self._resolve_workspace(db, data.workspace_id)
        style_examples = ""
        if data.use_style_memory:
            style_examples = await self.style_service.build_style_context(db)

        context = await self._get_context(
            workspace_id,
            data.thread[:2000],
            data.context_sources,
            data.use_knowledge_base,
        )
        prompt = build_reply_prompt(
            data.thread,
            style=data.style,
            context=context,
            style_examples=style_examples,
            extra_instructions=data.extra_instructions,
        )

        llm = await get_llm_provider(db)
        started = time.perf_counter()
        response = await llm.generate_text(prompt, system=CTO_SYSTEM_PROMPT)
        latency = int((time.perf_counter() - started) * 1000)

        thread_analysis = None
        if data.analyze_thread:
            thread_analysis = await self.analyze_thread(
                db, ThreadAnalyzeRequest(thread=data.thread, workspace_id=workspace_id)
            )

        suggestions = await self._generate_suggestions(db, response.content)

        email = EmailRecord(
            workspace_id=workspace_id,
            mode="reply",
            input_text=data.thread,
            generated_text=response.content,
            style=data.style,
            context_sources=data.context_sources,
            suggestions=suggestions.model_dump(),
            thread_analysis=thread_analysis.model_dump() if thread_analysis else None,
        )
        db.add(email)
        await db.flush()

        await self.log_service.create(
            db,
            action="reply",
            input_text=data.thread[:5000],
            prompt=prompt,
            llm_response=response.content,
            provider=response.provider,
            model=response.model,
            workspace_id=workspace_id,
            context_used=context or None,
            temperature=llm.config.temperature,
            tokens_used=response.tokens_used,
            latency_ms=latency,
            metadata={"email_id": email.id, "style": data.style},
        )

        return EmailGenerateResponse(
            id=email.id,
            generated_text=response.content,
            suggestions=suggestions,
            thread_analysis=thread_analysis,
            context_used=context or None,
            provider=response.provider,
            model=response.model,
        )

    async def rewrite(
        self, db: AsyncSession, data: RewriteRequest
    ) -> EmailGenerateResponse:
        workspace_id = await self._resolve_workspace(db, data.workspace_id)
        prompt = build_rewrite_prompt(data.text, data.mode)
        llm = await get_llm_provider(db)
        started = time.perf_counter()
        response = await llm.generate_text(prompt, system=CTO_SYSTEM_PROMPT)
        latency = int((time.perf_counter() - started) * 1000)

        email = EmailRecord(
            workspace_id=workspace_id,
            mode="rewrite",
            input_text=data.text,
            generated_text=response.content,
            rewrite_mode=data.mode,
        )
        db.add(email)
        await db.flush()

        await self.log_service.create(
            db,
            action="rewrite",
            input_text=data.text,
            prompt=prompt,
            llm_response=response.content,
            provider=response.provider,
            model=response.model,
            workspace_id=workspace_id,
            temperature=llm.config.temperature,
            tokens_used=response.tokens_used,
            latency_ms=latency,
            metadata={"mode": data.mode, "email_id": email.id},
        )

        return EmailGenerateResponse(
            id=email.id,
            generated_text=response.content,
            provider=response.provider,
            model=response.model,
        )

    async def save_final(
        self,
        db: AsyncSession,
        email_id: int,
        final_text: str,
        use_as_style_example: bool = True,
    ) -> Optional[EmailRecord]:
        result = await db.execute(select(EmailRecord).where(EmailRecord.id == email_id))
        email = result.scalar_one_or_none()
        if not email:
            return None
        email.final_text = final_text
        if use_as_style_example:
            email.used_as_style_example = True
            await self.style_service.add_example(
                db,
                content=final_text,
                category="sent_email",
                email_id=email.id,
            )
        await db.flush()
        return email

    async def list_emails(
        self,
        db: AsyncSession,
        workspace_id: Optional[int] = None,
        limit: int = 50,
    ) -> list[EmailRecord]:
        query = select(EmailRecord).order_by(EmailRecord.created_at.desc()).limit(limit)
        if workspace_id is not None:
            query = query.where(EmailRecord.workspace_id == workspace_id)
        result = await db.execute(query)
        return list(result.scalars().all())
