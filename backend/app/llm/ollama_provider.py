"""Ollama local LLM provider."""

from typing import Optional

import httpx

from app.llm.base import BaseLLMProvider, LLMConfig, LLMMessage, LLMResponse


class OllamaProvider(BaseLLMProvider):
    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self.base_url = (config.base_url or "http://localhost:11434").rstrip("/")

    async def generate(
        self,
        messages: list[LLMMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        payload = {
            "model": self.config.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": False,
            "options": {
                "temperature": temperature
                if temperature is not None
                else self.config.temperature,
                "num_predict": max_tokens
                if max_tokens is not None
                else self.config.max_tokens,
            },
        }
        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await client.post(f"{self.base_url}/api/chat", json=payload)
            response.raise_for_status()
            data = response.json()

        content = data.get("message", {}).get("content", "")
        return LLMResponse(
            content=content,
            provider="ollama",
            model=self.config.model,
            tokens_used=data.get("eval_count"),
            finish_reason=data.get("done_reason"),
            raw=data,
        )

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                return response.status_code == 200
        except Exception:
            return False

    async def list_models(self) -> list[str]:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{self.base_url}/api/tags")
            response.raise_for_status()
            data = response.json()
            return [m["name"] for m in data.get("models", [])]
