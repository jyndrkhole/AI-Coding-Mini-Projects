"""Groq LLM client for product intelligence."""

from __future__ import annotations

import json
import re
from typing import Any

from groq import Groq

from src.config import GROQ_API_KEY, GROQ_MODEL


class GroqService:
    """Thin wrapper around Groq chat completions with JSON extraction."""

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        key = (api_key or GROQ_API_KEY).strip()
        if not key or key == "your_groq_api_key_here":
            raise ValueError(
                "GROQ_API_KEY is missing. Add your free key from "
                "https://console.groq.com/keys to the .env file."
            )
        self.client = Groq(api_key=key)
        self.model = model or GROQ_MODEL

    def chat(
        self,
        system: str,
        user: str,
        *,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return (response.choices[0].message.content or "").strip()

    def chat_json(
        self,
        system: str,
        user: str,
        *,
        temperature: float = 0.2,
        max_tokens: int = 4096,
    ) -> dict[str, Any] | list[Any]:
        raw = self.chat(
            system + "\n\nRespond with valid JSON only. No markdown fences.",
            user,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return _parse_json(raw)


def _parse_json(text: str) -> dict[str, Any] | list[Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", cleaned)
        if not match:
            raise ValueError(f"Could not parse JSON from model response: {text[:200]}")
        return json.loads(match.group(1))
