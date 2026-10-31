from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.core.security import create_access_token, hash_password, verify_password
from app.database.connection import get_db
from app.database.models import User
from app.database.repositories.accounts import UserRepository, user_public

router = APIRouter(prefix="/api/auth", tags=["auth"])


class RegisterIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class ProfileIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(body: RegisterIn, db: Session = Depends(get_db)):
    repo = UserRepository(db)
    if repo.by_email(body.email):
        raise HTTPException(status.HTTP_409_CONFLICT, detail={"code": "exists", "message": "An account with that email already exists."})
    user = repo.create(body.name, str(body.email), hash_password(body.password), role="user")
    token = create_access_token(user.id, user.role)
    return {"success": True, "data": {"token": token, "user": user_public(user)}}


@router.post("/login")
def login(body: LoginIn, db: Session = Depends(get_db)):
    user = UserRepository(db).by_email(str(body.email))
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail={"code": "unauthorized", "message": "Email or password is wrong."})
    token = create_access_token(user.id, user.role)
    return {"success": True, "data": {"token": token, "user": user_public(user)}}


@router.get("/me")
def me(user: User = Depends(current_user)):
    return {"success": True, "data": user_public(user)}


@router.put("/me")
def update_me(body: ProfileIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    user.name = body.name.strip()
    db.commit()
    db.refresh(user)
    return {"success": True, "data": user_public(user)}
