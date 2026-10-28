"""Request dependencies. A token is required only when NPS_API_TOKEN is set."""

import os

from fastapi import HTTPException, Request


def db_session(request: Request):
    session = request.app.state.session_factory()
    try:
        yield session
    finally:
        session.close()


def require_access(request: Request) -> None:
    expected = os.environ.get("NPS_API_TOKEN", "").strip()
    if not expected:
        return
    header = request.headers.get("authorization", "")
    if header != f"Bearer {expected}":
        raise HTTPException(status_code=401, detail="Unauthorized")
