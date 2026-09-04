from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field

from app.db.models import Role, SensitivityGroup


class RegisterRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=160)
    password: str = Field(min_length=10, max_length=200,
                          description="At least 10 characters.")
    home_city_slug: str | None = None
    sensitivity_group: SensitivityGroup = SensitivityGroup.general


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_minutes: int


class UserOut(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    role: Role
    sensitivity_group: SensitivityGroup
    home_city_id: int | None = None

    model_config = {"from_attributes": True}


class UpdateProfileRequest(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=160)
    home_city_slug: str | None = None
    sensitivity_group: SensitivityGroup | None = None


class RoleUpdateRequest(BaseModel):
    role: Role
