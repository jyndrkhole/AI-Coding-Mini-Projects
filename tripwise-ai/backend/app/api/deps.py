"""Shared API dependencies."""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.database.connection import get_db
from app.database.models import User
from app.database.repositories.accounts import UserRepository

bearer = HTTPBearer(auto_error=False)


def current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail={"code": "unauthorized", "message": "Sign in to continue."})
    try:
        payload = decode_access_token(credentials.credentials)
        user = UserRepository(db).by_id(int(payload["sub"]))
    except Exception as exc:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail={"code": "unauthorized", "message": "Sign in again."},
        ) from exc
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail={"code": "unauthorized", "message": "Sign in again."})
    return user


def require_admin(user: User = Depends(current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail={"code": "forbidden", "message": "Admin access is required."})
    return user
