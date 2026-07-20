from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Integer, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TenantAuditMixin


class AuditoriaIA(TenantAuditMixin, Base):
    __tablename__ = "auditorias_ia"

    reporte_id: Mapped[int] = mapped_column(ForeignKey("quality_reports_8d.id", ondelete="CASCADE"), nullable=False, index=True)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    hallazgos: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    aprobado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    raw_response: Mapped[str] = mapped_column(Text, nullable=False, default="")

    reporte = relationship("QualityReport8D", back_populates="auditorias")

