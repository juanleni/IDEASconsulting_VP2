from __future__ import annotations

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TenantAuditMixin


class QualityReport8D(TenantAuditMixin, Base):
    __tablename__ = "quality_reports_8d"

    titulo: Mapped[str] = mapped_column(String(255), nullable=False)
    d2_problema: Mapped[str] = mapped_column(Text, nullable=False, default="")
    d4_causa_raiz: Mapped[str] = mapped_column(Text, nullable=False, default="")
    d5_acciones: Mapped[str] = mapped_column(Text, nullable=False, default="")

    auditorias: Mapped[list["AuditoriaIA"]] = relationship(back_populates="reporte", cascade="all,delete-orphan")


from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.auditoria_ia import AuditoriaIA

