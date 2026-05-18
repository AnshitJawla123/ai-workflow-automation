from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ...db.session import get_db
from ...models import User
from ...core.security import verify_password, create_access_token, hash_password
from ...schemas.auth import LoginRequest, TokenResponse
from ...schemas.common import Msg
from ..deps import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
    token = create_access_token(user.email, role=user.role)
    return TokenResponse(access_token=token, role=user.role, email=user.email)


@router.post("/register", response_model=TokenResponse)
def register(payload: LoginRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(400, "Email already registered")
    user = User(email=payload.email, password_hash=hash_password(payload.password), role="viewer")
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token(user.email, role=user.role)
    return TokenResponse(access_token=token, role=user.role, email=user.email)


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return {"id": user.id, "email": user.email, "role": user.role}


@router.post("/logout", response_model=Msg)
def logout():
    # Stateless JWT — client just discards the token
    return Msg(message="Logged out")
