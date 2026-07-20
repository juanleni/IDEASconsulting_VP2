from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps.auth import get_current_tenant
from app.db.session import get_db_session
from app.services.auditor_service import AuditorService

router = APIRouter(prefix="/auditor", tags=["auditor"])


class AuditorResponse(BaseModel):
    score: int
    hallazgos: list[str]
    aprobado: bool


@router.post("/8d/{reporte_id}", response_model=AuditorResponse)
async def evaluar_reporte_8d(
    reporte_id: int,
    empresa_id: int = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_db_session),
) -> AuditorResponse:
    service = AuditorService()
    result = await service.evaluar_calidad_8d(session=session, empresa_id=empresa_id, reporte_id=reporte_id)
    return AuditorResponse(score=result.score, hallazgos=result.hallazgos, aprobado=result.aprobado)
