from __future__ import annotations

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import audit, get_current_user, require_role
from app.core.config import settings
from app.core.errors import InvalidRequest, NotAuthorized
from app.core.security import create_access_token, hash_password, verify_password
from app.db.models import City, Role, User
from app.db.session import get_db
from app.schemas.auth import (LoginRequest, RegisterRequest, RoleUpdateRequest,
                               TokenResponse, UpdateProfileRequest, UserOut)

router = APIRouter(prefix="/auth", tags=["auth"])


def _resolve_city(db: Session, slug: str | None) -> int | None:
    if not slug:
        return None
    city = db.scalar(select(City).where(City.slug == slug))
    if city is None:
        raise InvalidRequest("Unknown city.")
    return city.id


@router.post("/register", response_model=TokenResponse,
             status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, request: Request,
             db: Session = Depends(get_db)) -> TokenResponse:
    """Public self-registration always creates a **citizen**. Analyst, official
    and admin roles are granted by an admin — never claimable by the client."""
    email = payload.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise InvalidRequest("An account with that email already exists.")

    user = User(email=email, full_name=payload.full_name.strip(),
                hashed_password=hash_password(payload.password),
                role=Role.citizen,
                home_city_id=_resolve_city(db, payload.home_city_slug),
                sensitivity_group=payload.sensitivity_group)
    db.add(user)
    db.commit()
    audit(db, request, "user.register", user=user, resource=email)
    return TokenResponse(
        access_token=create_access_token(user.email, user.role.value),
        expires_in_minutes=settings.airs_access_token_minutes)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, request: Request,
          db: Session = Depends(get_db)) -> TokenResponse:
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    # Same message for "no such user" and "wrong password" — do not leak which.
    if user is None or not verify_password(payload.password, user.hashed_password):
        audit(db, request, "user.login", resource=payload.email.lower(),
              outcome="failure")
        raise NotAuthorized("Incorrect email or password.")
    if not user.is_active:
        raise NotAuthorized("This account has been deactivated.")
    audit(db, request, "user.login", user=user)
    return TokenResponse(
        access_token=create_access_token(user.email, user.role.value),
        expires_in_minutes=settings.airs_access_token_minutes)


@router.post("/logout")
def logout(request: Request, user: User = Depends(get_current_user),
           db: Session = Depends(get_db)) -> dict:
    """Tokens are stateless and short-lived; the client discards it. Recorded
    for the audit trail."""
    audit(db, request, "user.logout", user=user)
    return {"message": "Signed out."}


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> User:
    return user


@router.patch("/me", response_model=UserOut)
def update_me(payload: UpdateProfileRequest, user: User = Depends(get_current_user),
              db: Session = Depends(get_db)) -> User:
    if payload.full_name is not None:
        user.full_name = payload.full_name.strip()
    if payload.sensitivity_group is not None:
        user.sensitivity_group = payload.sensitivity_group
    if payload.home_city_slug is not None:
        user.home_city_id = _resolve_city(db, payload.home_city_slug)
    db.commit()
    return user


@router.get("/users", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db),
               _: User = Depends(require_role(Role.admin))) -> list[User]:
    return list(db.scalars(select(User).order_by(User.created_at.desc())))


@router.patch("/users/{user_id}/role", response_model=UserOut)
def set_role(user_id: int, payload: RoleUpdateRequest, request: Request,
             db: Session = Depends(get_db),
             actor: User = Depends(require_role(Role.admin))) -> User:
    target = db.get(User, user_id)
    if target is None:
        raise InvalidRequest("No such user.")
    if target.id == actor.id and payload.role != Role.admin:
        raise InvalidRequest("You cannot remove your own admin role.")
    target.role = payload.role
    db.commit()
    audit(db, request, "user.role_change", user=actor, resource=target.email,
          context={"new_role": payload.role.value})
    return target
