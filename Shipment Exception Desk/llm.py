"""Shared LangChain chat model. Groq is the default (free) provider."""

import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

PROVIDER = os.getenv("PROVIDER", "groq").strip().lower()


def _looks_like_key(value: str | None) -> bool:
    return bool(value) and not value.strip().startswith("your_")


def get_chat_model(temperature: float = 0) -> ChatOpenAI:
    """Return the class chat model. Temperature 0 keeps classification stable."""
    if PROVIDER == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        if not _looks_like_key(api_key):
            raise RuntimeError("Set OPENAI_API_KEY in .env to use PROVIDER=openai.")
        return ChatOpenAI(model="gpt-4o-mini", api_key=api_key, temperature=temperature)

    api_key = os.getenv("GROQ_API_KEY")
    if not _looks_like_key(api_key):
        raise RuntimeError(
            "Set GROQ_API_KEY in .env. Get a free key at https://console.groq.com"
        )
    return ChatOpenAI(
        model=os.getenv("GROQ_MODEL", "openai/gpt-oss-20b"),
        api_key=api_key,
        base_url="https://api.groq.com/openai/v1",
        temperature=temperature,
    )
