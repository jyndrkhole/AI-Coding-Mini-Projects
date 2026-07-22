"""Optional Groq-powered assistant for build log analysis."""

from __future__ import annotations

from config import settings

SYSTEM_PROMPT = """You are a senior iOS / Android / .NET MAUI release engineer assistant.
You help diagnose TestFlight (iOS) and Android AAB build failures.
Be concise, actionable, and specific. Reference line numbers or error codes when visible in logs.
If the build succeeded, give a brief confirmation and what to expect next (TestFlight processing or Play internal testing).
"""


async def analyze_logs(logs: str, question: str | None = None) -> str:
    if not settings.groq_api_key:
        return (
            "Groq API key not configured. Add GROQ_API_KEY to your .env file "
            "(free at https://console.groq.com). The release pipeline works without it."
        )

    try:
        from groq import AsyncGroq
    except ImportError:
        return "Install groq: pip install groq"

    client = AsyncGroq(api_key=settings.groq_api_key)

    user_content = f"Build logs:\n\n```\n{logs[-12000:]}\n```"
    if question:
        user_content += f"\n\nUser question: {question}"
    else:
        user_content += "\n\nSummarize what happened and flag any issues or next steps."

    response = await client.chat.completions.create(
        model=settings.groq_model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        max_tokens=1024,
        temperature=0.2,
    )

    return response.choices[0].message.content or "No response from model."
