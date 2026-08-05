"""LLM provider abstraction — interchangeable Ollama / Groq backends."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import List, Optional

import httpx

from backend.core.config import Settings, get_settings
from backend.core.logging import get_logger
from backend.core.privacy import (
    PrivacyError,
    assert_cloud_llm_allowed,
    assert_ollama_is_local,
)
from backend.models.schemas import (
    ExplainRequest,
    ExplainResponse,
    LLMAction,
)

logger = get_logger(__name__)


class LLMProvider(ABC):
    """Abstract LLM provider."""

    name: str

    @abstractmethod
    async def complete(self, system_prompt: str, user_prompt: str, model: Optional[str] = None) -> str:
        ...


class OllamaProvider(LLMProvider):
    name = "ollama"

    def __init__(self, settings: Settings) -> None:
        self._base = settings.ollama_base_url.rstrip("/")
        self._model = settings.ollama_model

    async def complete(self, system_prompt: str, user_prompt: str, model: Optional[str] = None) -> str:
        payload = {
            "model": model or self._model,
            "stream": False,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(f"{self._base}/api/chat", json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data.get("message", {}).get("content") or data.get("response") or ""


class GroqProvider(LLMProvider):
    name = "groq"

    def __init__(self, settings: Settings) -> None:
        self._api_key = settings.groq_api_key
        self._base = settings.groq_base_url.rstrip("/")
        self._model = settings.groq_model

    async def complete(self, system_prompt: str, user_prompt: str, model: Optional[str] = None) -> str:
        if not self._api_key:
            raise ValueError("GROQ_API_KEY is not configured")

        payload = {
            "model": model or self._model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
        }
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{self._base}/chat/completions", json=payload, headers=headers
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]


def get_provider(name: Optional[str] = None, settings: Optional[Settings] = None) -> LLMProvider:
    settings = settings or get_settings()
    provider_name = (name or settings.llm_provider or "ollama").lower()
    assert_cloud_llm_allowed(settings, provider_name)
    if provider_name == "groq":
        return GroqProvider(settings)
    if provider_name == "ollama":
        if not settings.allow_local_llm:
            raise PrivacyError(
                "Local LLM is disabled. Validation still works without AI."
            )
        assert_ollama_is_local(settings.ollama_base_url)
        return OllamaProvider(settings)
    raise ValueError(f"Unknown LLM provider: {provider_name}")


SYSTEM_PROMPTS = {
    LLMAction.EXPLAIN_ERRORS: (
        "You are an API schema expert. Explain validation errors clearly for engineers. "
        "Be concise, use bullet points, and avoid inventing schema rules."
    ),
    LLMAction.SUGGEST_FIX: (
        "You are an API schema expert. Suggest concrete fixes for each validation error. "
        "Show corrected JSON snippets where helpful. Do not claim the response was re-validated."
    ),
    LLMAction.GENERATE_CORRECT_JSON: (
        "You are an API schema expert. Generate a complete, valid JSON example that "
        "conforms to the provided schema / selected response schema. Output JSON only."
    ),
    LLMAction.EXPLAIN_SCHEMA: (
        "You are an API schema expert. Explain the schema structure, required fields, "
        "types, constraints, and composition keywords (oneOf/anyOf/allOf) in plain language."
    ),
}


class LLMService:
    """Optional AI assistance — never used by the core validation path."""

    async def explain(self, request: ExplainRequest) -> ExplainResponse:
        try:
            provider = get_provider(request.provider)
            system = SYSTEM_PROMPTS[request.action]
            user = self._build_user_prompt(request)
            # AI is explicit opt-in only; never called from validate path.
            content = await provider.complete(system, user, model=request.model)
            return ExplainResponse(
                success=True,
                action=request.action,
                content=content,
                provider=provider.name,
                model=request.model,
            )
        except PrivacyError as exc:
            logger.warning("LLM blocked by privacy policy: %s", type(exc).__name__)
            return ExplainResponse(
                success=False,
                action=request.action,
                error=str(exc),
                provider=request.provider,
                model=request.model,
            )
        except Exception as exc:
            # Do not log prompt/schema/response bodies.
            logger.exception("LLM request failed: %s", type(exc).__name__)
            return ExplainResponse(
                success=False,
                action=request.action,
                error=str(exc),
                provider=request.provider,
                model=request.model,
            )

    def _build_user_prompt(self, request: ExplainRequest) -> str:
        parts: List[str] = [f"Action: {request.action.value}"]

        if request.errors:
            parts.append("Validation errors:")
            parts.append(json.dumps([e.model_dump(mode="json") for e in request.errors], indent=2))

        if request.schema_content:
            truncated = request.schema_content[:12000]
            parts.append("Schema (may be truncated):\n```\n" + truncated + "\n```")

        if request.response_content:
            truncated = request.response_content[:12000]
            parts.append("API response (may be truncated):\n```json\n" + truncated + "\n```")

        return "\n\n".join(parts)
