"""Groq LLM provider."""

from typing import Optional

from groq import AsyncGroq

from app.llm.base import BaseLLMProvider, LLMConfig, LLMMessage, LLMResponse


class GroqProvider(BaseLLMProvider):
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        if not config.api_key:
            raise ValueError("GROQ_API_KEY is required for Groq provider")
        self.client = AsyncGroq(api_key=config.api_key)

    async def generate(
        self,
        messages: list[LLMMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        response = await self.client.chat.completions.create(
            model=self.config.model,
            messages=[{"role": m.role, "content": m.content} for m in messages],
            temperature=temperature if temperature is not None else self.config.temperature,
            max_tokens=max_tokens if max_tokens is not None else self.config.max_tokens,
        )
        choice = response.choices[0]
        return LLMResponse(
            content=choice.message.content or "",
            provider="groq",
            model=self.config.model,
            tokens_used=response.usage.total_tokens if response.usage else None,
            finish_reason=choice.finish_reason,
            raw={"id": response.id},
        )

    async def health_check(self) -> bool:
        try:
            models = await self.client.models.list()
            return bool(models.data)
        except Exception:
            return False
