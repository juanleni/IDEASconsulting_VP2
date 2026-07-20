from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps.auth import get_current_tenant
from app.db.session import get_db_session
from app.services.quality8d_service import Quality8DService

router = APIRouter(prefix="/quality", tags=["quality"])


@router.get("/8d")
async def list_quality_8d(
    empresa_id: int = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_db_session),
) -> list[dict]:
    service = Quality8DService(session=session, empresa_id=empresa_id)
    rows = await service.list_reports()
    return [
        {
            "id": item.id,
            "empresa_id": item.empresa_id,
            "titulo": item.titulo,
            "d2_problema": item.d2_problema,
            "d4_causa_raiz": item.d4_causa_raiz,
            "d5_acciones": item.d5_acciones,
        }
        for item in rows
    ]

