"""Host-side MCP client. The advisor process does not query destination prices itself."""

from __future__ import annotations

import json
import os
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from app.core.config import BACKEND_ROOT, get_settings


def server_parameters() -> StdioServerParameters:
    settings = get_settings()
    env = os.environ.copy()
    env["SQLITE_PATH"] = str(settings.sqlite_file)
    env["PYTHONUNBUFFERED"] = "1"
    return StdioServerParameters(
        command=sys.executable,
        args=["-m", "app.mcp.server"],
        cwd=str(BACKEND_ROOT),
        env=env,
    )


@asynccontextmanager
async def open_session() -> AsyncIterator[ClientSession]:
    async with stdio_client(server_parameters()) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session


def mcp_tool_to_openai(tool) -> dict:
    """MCP name + description + inputSchema becomes the OpenAI tool shape."""
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description or "",
            "parameters": tool.inputSchema,
        },
    }


def result_text(result) -> str:
    if getattr(result, "structuredContent", None) is not None:
        data = result.structuredContent
        if isinstance(data, dict) and set(data) == {"result"}:
            data = data["result"]
        return json.dumps(data, ensure_ascii=False)
    blocks = []
    for block in result.content:
        if getattr(block, "type", None) == "text":
            blocks.append(block.text)
    return "\n".join(blocks)


def parse_tool_payload(result) -> dict | list:
    text = result_text(result)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"text": text, "is_error": bool(result.isError)}
