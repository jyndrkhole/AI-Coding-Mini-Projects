"""Chat model. Groq is preferred when GROQ_API_KEY is set. The key stays server-side."""

from langchain_openai import ChatOpenAI

from app.core.config import get_settings


class LLMNotConfigured(RuntimeError):
    pass


def get_chat_model() -> ChatOpenAI:
    settings = get_settings()
    if settings.groq_api_key.strip():
        return ChatOpenAI(
            model=settings.groq_model,
            api_key=settings.groq_api_key,
            base_url=settings.groq_base_url,
            temperature=0,
            timeout=60,
            max_retries=1,
        )
    if settings.openai_api_key.strip():
        kwargs = {
            "model": settings.openai_model,
            "api_key": settings.openai_api_key,
            "temperature": 0,
            "timeout": 60,
            "max_retries": 1,
        }
        if settings.openai_base_url.strip():
            kwargs["base_url"] = settings.openai_base_url
        model_name = settings.openai_model.lower()
        if model_name.startswith("gpt-6") or model_name.startswith("o"):
            kwargs.pop("temperature", None)
            kwargs["reasoning_effort"] = "none"
        return ChatOpenAI(**kwargs)
    raise LLMNotConfigured("Set GROQ_API_KEY or OPENAI_API_KEY in the backend environment.")
