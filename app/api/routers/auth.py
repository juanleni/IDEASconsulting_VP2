from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps.auth import get_current_user
from app.db.session import get_db_session
from app.models.usuario import Usuario
from app.schemas.auth import CurrentUserResponse, LoginRequest, TokenResponse
from app.services.auth_service import authenticate_user, create_access_token, normalize_login_identifier

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, session: AsyncSession = Depends(get_db_session)) -> TokenResponse:
    user = await authenticate_user(
        session=session,
        email=normalize_login_identifier(payload.email),
        password=payload.password,
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o password invalidos.",
        )
    return create_access_token(user)


@router.get("/me", response_model=CurrentUserResponse)
async def me(user: Usuario = Depends(get_current_user)) -> CurrentUserResponse:
    return CurrentUserResponse(
        user_id=int(user.id),
        empresa_id=int(user.empresa_id),
        email=user.email,
        rol=user.rol,
    )
