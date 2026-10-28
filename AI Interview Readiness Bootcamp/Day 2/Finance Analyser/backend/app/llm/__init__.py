"""Chat-completions client for Groq or OpenAI. Commentary only; never the rating."""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from app.config import Settings

log = logging.getLogger(__name__)


class LLMClient:
    def __init__(self, settings: Settings) -> None:
        status = settings.llm_status()
        self.provider = str(status["provider"])
        self.model = str(status["model"])
        self.configured = bool(status["configured"])
        self.message = str(status["message"])
        self._settings = settings

    async def complete_json(self, system: str, user: str) -> dict[str, Any] | None:
        if not self.configured:
            return None
        payload = {
            "model": self.model,
            "temperature": 0.2,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "response_format": {"type": "json_object"},
        }
        try:
            content = await self._post(payload)
        except Exception:
            payload.pop("response_format", None)
            try:
                content = await self._post(payload)
            except Exception:
                log.warning("LLM request failed for provider %s. Commentary will be rule-based.", self.provider)
                return None
        return _parse_json(content)

    async def _post(self, payload: dict) -> str:
        if self.provider == "groq":
            url = "https://api.groq.com/openai/v1/chat/completions"
            key = self._settings.groq_api_key
        elif self.provider == "openai":
            url = "https://api.openai.com/v1/chat/completions"
            key = self._settings.openai_api_key
        else:
            raise RuntimeError(self.message or "LLM provider is not configured.")
        last_error: Exception | None = None
        for _ in range(2):
            try:
                async with httpx.AsyncClient(timeout=45) as client:
                    response = await client.post(
                        url,
                        headers={"Authorization": f"Bearer {key}"},
                        json=payload,
                    )
                if response.status_code >= 400:
                    last_error = RuntimeError(f"LLM HTTP {response.status_code}")
                    continue
                body = response.json()
                return body["choices"][0]["message"]["content"]
            except Exception as exc:
                last_error = exc
        raise RuntimeError("LLM request failed") from last_error


def _parse_json(content: str) -> dict | None:
    text = content.strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text.removeprefix("json").strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start < 0 or end <= start:
            return None
        try:
            parsed = json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return None
    return parsed if isinstance(parsed, dict) else None
