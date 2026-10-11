"""Optional model call. A missing model or a failed request returns None so the caller can show stored evidence."""

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def complete(system: str, user: str) -> str | None:
    settings = get_settings()
    provider = (settings.ai_provider or "").lower()
    try:
        if provider == "ollama":
            return _ollama(settings.ollama_base_url, settings.ollama_model, system, user)
        if provider in {"groq", "xai"}:
            return _groq(provider, settings.groq_api_key, settings.groq_model, system, user)
        if provider == "bedrock":
            return _bedrock(settings.aws_bedrock_region, settings.aws_bedrock_model_id, system, user)
    except Exception:
        logger.exception("Advisor model call failed")
        return None
    return None


def _ollama(base_url: str, model: str, system: str, user: str) -> str | None:
    if not model.strip():
        return None
    response = httpx.post(
        f"{base_url.rstrip('/')}/api/chat",
        json={
            "model": model,
            "stream": False,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        },
        timeout=30,
    )
    response.raise_for_status()
    content = response.json().get("message", {}).get("content")
    return content.strip() if isinstance(content, str) and content.strip() else None


def _groq(provider: str, api_key: str, model: str, system: str, user: str) -> str | None:
    key = api_key.strip()
    if not key:
        return None
    chosen = model.strip()
    if key.startswith("xai-") or provider == "xai":
        url = "https://api.x.ai/v1/chat/completions"
        chosen = chosen or "grok-4.7"
        timeout = 90
    else:
        url = "https://api.groq.com/openai/v1/chat/completions"
        timeout = 30
    if not chosen:
        return None
    payload = {
        "model": chosen,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    if "gpt-oss" in chosen:
        payload["max_tokens"] = 800
        payload["reasoning_effort"] = "low"
    response = httpx.post(
        url,
        headers={"Authorization": f"Bearer {key}"},
        json=payload,
        timeout=timeout,
    )
    response.raise_for_status()
    content = response.json()["choices"][0]["message"]["content"]
    return content.strip() if isinstance(content, str) and content.strip() else None


def _bedrock(region: str, model_id: str, system: str, user: str) -> str | None:
    if not model_id.strip():
        return None
    from app.aws.credentials import aws_session

    client = aws_session().client("bedrock-runtime", region_name=region)
    payload = client.converse(
        modelId=model_id,
        system=[{"text": system}],
        messages=[{"role": "user", "content": [{"text": user}]}],
    )
    text = payload["output"]["message"]["content"][0]["text"]
    return text.strip() if isinstance(text, str) and text.strip() else None
