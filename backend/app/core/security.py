"""Password hashing and JWT issuing/validation."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return pwd_context.verify(plain, hashed)
    except ValueError:
        return False


def create_access_token(subject: str, role: str,
                        expires_minutes: int | None = None) -> str:
    minutes = expires_minutes or settings.airs_access_token_minutes
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": subject,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=minutes)).timestamp()),
        "iss": "airs",
    }
    return jwt.encode(payload, settings.airs_secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.airs_secret_key, algorithms=[ALGORITHM],
                          issuer="airs")
    except JWTError:
        return None
