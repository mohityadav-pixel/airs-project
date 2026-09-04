"""FastAPI dependencies: DB session, current user, role gates."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import Depends, Header, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import NotAuthorized
from app.core.security import decode_access_token
from app.db.models import AuditLog, Role, User
from app.db.session import get_db

ROLE_RANK = {Role.citizen: 0, Role.analyst: 1, Role.official: 2, Role.admin: 3}


def _extract_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    return token if scheme.lower() == "bearer" and token else None


def get_current_user_optional(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User | None:
    token = _extract_token(authorization)
    if not token:
        return None
    payload = decode_access_token(token)
    if not payload:
        return None
    user = db.scalar(select(User).where(User.email == payload.get("sub")))
    if user is None or not user.is_active:
        return None
    return user


def get_current_user(user: User | None = Depends(get_current_user_optional)) -> User:
    if user is None:
        raise NotAuthorized("Sign in to continue.")
    return user


def require_role(minimum: Role):
    """Hierarchical gate: admin >= official >= analyst >= citizen."""

    def _dep(user: User = Depends(get_current_user)) -> User:
        if ROLE_RANK[user.role] < ROLE_RANK[minimum]:
            raise NotAuthorized(
                f"This action requires the {minimum.value} role or higher.")
        return user

    return _dep


def audit(db: Session, request: Request, action: str, *, user: User | None = None,
          resource: str | None = None, outcome: str = "success",
          context: dict | None = None) -> None:
    db.add(AuditLog(at=datetime.now(timezone.utc),
                    user_id=user.id if user else None, action=action,
                    resource=resource, outcome=outcome,
                    context={"path": request.url.path, **(context or {})}))
    db.commit()
