from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime
    user_id: int
    empresa_id: int
    rol: str


class TokenPayload(BaseModel):
    sub: str
    user_id: int
    empresa_id: int
    rol: str
    exp: int


class CurrentUserResponse(BaseModel):
    user_id: int
    empresa_id: int
    email: str
    rol: str
