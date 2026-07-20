from __future__ import annotations

from datetime import datetime, timedelta, timezone

from jose import jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.usuario import Usuario
from app.schemas.auth import TokenResponse


password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def normalize_login_identifier(value: str) -> str:
    identifier = str(value or "").strip().lower()
    if identifier and "@" not in identifier:
        return f"{identifier}@ideas.local"
    return identifier


def hash_password(password: str) -> str:
    return password_context.hash(password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    return password_context.verify(plain_password, password_hash)


def create_access_token(user: Usuario) -> TokenResponse:
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_access_token_expire_minutes)
    payload = {
        "sub": user.email,
        "user_id": user.id,
        "empresa_id": user.empresa_id,
        "rol": user.rol,
        "exp": expires_at,
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return TokenResponse(
        access_token=token,
        expires_at=expires_at,
        user_id=int(user.id),
        empresa_id=int(user.empresa_id),
        rol=user.rol,
    )


async def authenticate_user(session: AsyncSession, email: str, password: str) -> Usuario | None:
    stmt = select(Usuario).where(Usuario.email == normalize_login_identifier(email))
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    if not user or not verify_password(password, user.password_hash):
        return None
    return user
