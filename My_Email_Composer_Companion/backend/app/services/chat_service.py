"""Chat workspace service."""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import ChatMessage
from app.llm.factory import get_llm_provider
from app.prompts.templates import CTO_SYSTEM_PROMPT, build_chat_prompt
from app.rag.retriever import Retriever
from app.schemas import ChatMessageOut, ChatRequest, ChatResponse
from app.services.log_service import LogService
from app.services.workspace_service import WorkspaceService


class ChatService:
    def __init__(self):
        self.retriever = Retriever()
        self.log_service = LogService()
        self.workspace_service = WorkspaceService()

    async def chat(self, db: AsyncSession, data: ChatRequest) -> ChatResponse:
        workspace_id = data.workspace_id
        if not workspace_id:
            default = await self.workspace_service.ensure_default(db)
            workspace_id = default.id

        user_msg = ChatMessage(
            workspace_id=workspace_id,
            role="user",
            content=data.message,
        )
        db.add(user_msg)
        await db.flush()

        result = await db.execute(
            select(ChatMessage)
            .where(ChatMessage.workspace_id == workspace_id)
            .order_by(ChatMessage.created_at.desc())
            .limit(10)
        )
        recent = list(reversed(result.scalars().all()))
        history = "\n".join(f"{m.role}: {m.content}" for m in recent[:-1])

        context = ""
        if data.use_knowledge_base:
            chunks = await self.retriever.retrieve(workspace_id, data.message)
            context = self.retriever.format_context(chunks)

        prompt = build_chat_prompt(data.message, context=context, history=history)
        llm = await get_llm_provider(db)
        response = await llm.generate_text(prompt, system=CTO_SYSTEM_PROMPT)

        assistant_msg = ChatMessage(
            workspace_id=workspace_id,
            role="assistant",
            content=response.content,
            context_used=context or None,
        )
        db.add(assistant_msg)
        await db.flush()

        await self.log_service.create(
            db,
            action="chat",
            input_text=data.message,
            prompt=prompt,
            llm_response=response.content,
            provider=response.provider,
            model=response.model,
            workspace_id=workspace_id,
            context_used=context or None,
            tokens_used=response.tokens_used,
        )

        return ChatResponse(
            reply=ChatMessageOut.model_validate(assistant_msg),
            context_used=context or None,
        )

    async def history(
        self, db: AsyncSession, workspace_id: Optional[int] = None, limit: int = 50
    ) -> list[ChatMessage]:
        query = select(ChatMessage).order_by(ChatMessage.created_at.asc()).limit(limit)
        if workspace_id is not None:
            query = query.where(ChatMessage.workspace_id == workspace_id)
        result = await db.execute(query)
        return list(result.scalars().all())
