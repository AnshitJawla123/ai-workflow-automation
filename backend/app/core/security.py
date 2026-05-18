"""JWT + password hashing."""
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import jwt, JWTError
from passlib.context import CryptContext

from .config import settings

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(pw: str) -> str:
    return _pwd.hash(pw)


def verify_password(pw: str, hashed: str) -> bool:
    try:
        return _pwd.verify(pw, hashed)
    except Exception:
        return False


def create_access_token(subject: str, role: str = "viewer", minutes: Optional[int] = None) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=minutes or settings.jwt_expires_minutes)
    payload = {"sub": subject, "role": role, "exp": expire}
    return jwt.encode(payload, settings.app_secret_key, algorithm=settings.jwt_algo)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.app_secret_key, algorithms=[settings.jwt_algo])
    except JWTError as e:
        raise ValueError(f"Invalid token: {e}")
