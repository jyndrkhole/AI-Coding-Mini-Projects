import json

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.ai.agent import run_agent
from app.ai.llm import LLMNotConfigured
from app.api.deps import current_user
from app.core.rate_limit import enforce_rate_limit
from app.database.connection import get_db
from app.database.models import User
from app.database.repositories.accounts import ChatRepository, serialize_message, serialize_session
from app.mcp.client import open_session, parse_tool_payload

router = APIRouter(prefix="/api/advisor", tags=["advisor"])


class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    session_id: int | None = None


def _plan_args(message: str) -> dict | None:
    parts = message.strip().split()
    if not parts or parts[0].lower() != "/plan":
        return None
    if len(parts) != 5:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail={"code": "bad_plan", "message": "Use /plan <place> <people> <nights> <budget per person>. Example: /plan Goa 4 3 12000"},
        )
    _, place, people, nights, budget = parts
    return {"place": place, "people": people, "nights": nights, "budget_per_person": budget}


@router.post("/chat")
async def chat(body: ChatIn, request: Request, user: User = Depends(current_user), db: Session = Depends(get_db)):
    enforce_rate_limit(f"advisor:{user.id}:{request.client.host if request.client else 'local'}")
    prompt_args = _plan_args(body.message)
    repo = ChatRepository(db)
    if body.session_id:
        session = repo.get_session(body.session_id, user.id)
        if session is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail={"code": "not_found", "message": "That conversation was not found."})
    else:
        title = body.message.strip()[:80] or "New trip"
        session = repo.create_session(user.id, title)
    history = [{"role": item.role, "content": item.content} for item in session.messages]
    if body.message.strip().lower() == "list":
        async with open_session() as mcp_session:
            result = await mcp_session.call_tool("list_destinations", {})
        places = parse_tool_payload(result)
        lines = ["Destinations in the catalogue (from the MCP tool list_destinations):"]
        if isinstance(places, list):
            for place in places:
                lines.append(f"- {place['name']} ({place['place_id']}) · {place['trip_type']} · {place['best_months']}")
        reply = "\n".join(lines)
        trace = [{"name": "list_destinations", "args": {}, "result": places, "is_error": bool(result.isError)}]
        resolved = body.message
        rag_context = ""
    else:
        try:
            outcome = await run_agent(body.message, history=history, prompt_args=prompt_args)
        except LLMNotConfigured as exc:
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail={"code": "llm_unconfigured", "message": str(exc)}) from exc
        except Exception as exc:
            raise HTTPException(
                status.HTTP_502_BAD_GATEWAY,
                detail={"code": "advisor_failed", "message": "The advisor could not finish. Try a shorter question."},
            ) from exc
        reply = outcome["reply"]
        trace = outcome["tool_trace"]
        resolved = outcome["resolved_message"]
        rag_context = outcome["rag_context"]
    repo.add_message(session, "user", body.message)
    repo.add_message(
        session,
        "assistant",
        reply,
        {"tool_trace": trace, "rag_context": rag_context, "resolved_message": resolved},
    )
    db.refresh(session)
    return {
        "success": True,
        "data": {
            "session": serialize_session(session),
            "reply": reply,
            "resolved_message": resolved,
            "tool_trace": trace,
        },
    }


@router.get("/sessions")
def list_sessions(user: User = Depends(current_user), db: Session = Depends(get_db)):
    sessions = ChatRepository(db).list_sessions(user.id)
    return {"success": True, "data": [serialize_session(item) for item in sessions]}


@router.get("/sessions/{session_id}")
def get_session(session_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    session = ChatRepository(db).get_session(session_id, user.id)
    if session is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail={"code": "not_found", "message": "That conversation was not found."})
    payload = serialize_session(session, with_messages=True)
    payload["messages"] = [serialize_message(item) for item in session.messages]
    return {"success": True, "data": payload}


@router.delete("/sessions/{session_id}")
def delete_session(session_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    repo = ChatRepository(db)
    session = repo.get_session(session_id, user.id)
    if session is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail={"code": "not_found", "message": "That conversation was not found."})
    repo.delete_session(session)
    return {"success": True, "data": {"deleted": True}}
