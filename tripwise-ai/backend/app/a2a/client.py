"""Ask the Local Guide agent. MCP stays the price path. This is the other agent."""

from __future__ import annotations

import logging

import httpx
from a2a.client import ClientConfig, create_client
from a2a.helpers import get_stream_response_text, new_text_message
from a2a.types import Role, SendMessageRequest

from app.core.config import get_settings

logger = logging.getLogger(__name__)

GUIDE_TOOL = {
    "type": "function",
    "function": {
        "name": "ask_local_guide",
        "description": "Ask the Local Guide agent what to do, what local food to try and what weather to expect at a destination in a given month.",
        "parameters": {
            "type": "object",
            "required": ["place", "month"],
            "properties": {
                "place": {"type": "string", "description": "Destination name, for example Hampi"},
                "month": {"type": "string", "description": "Month of travel, for example December"},
            },
        },
    },
}


async def ask_local_guide(place: str, month: str) -> str:
    question = f"What should a group of friends do in {place} in {month}?"
    url = get_settings().guide_url
    http = httpx.AsyncClient(timeout=8.0)
    try:
        client = await create_client(url, ClientConfig(streaming=False, httpx_client=http))
        request = SendMessageRequest(message=new_text_message(question, role=Role.ROLE_USER))
        answer = ""
        async for response in client.send_message(request):
            answer += get_stream_response_text(response)
        await client.close()
        return answer or "The Local Guide agent replied with an empty note."
    except Exception:
        logger.info("local guide unavailable at %s", url)
        return "The Local Guide agent is offline. Start it with: python -m app.a2a.guide. Prices can still be answered from the catalogue."
    finally:
        await http.aclose()
