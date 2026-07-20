from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.quality_report import QualityReport8D
from app.repositories.base_repository import BaseRepository


class Quality8DService:
    def __init__(self, session: AsyncSession, empresa_id: int) -> None:
        self.repo = BaseRepository(QualityReport8D, session=session, empresa_id=empresa_id)

    async def list_reports(self) -> list[QualityReport8D]:
        return await self.repo.list(limit=200)

    async def get_report(self, reporte_id: int) -> QualityReport8D | None:
        return await self.repo.get(reporte_id)

