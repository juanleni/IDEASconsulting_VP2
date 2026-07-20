from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TenantAuditMixin

if TYPE_CHECKING:
    from app.models.usuario import Usuario


class Empresa(TenantAuditMixin, Base):
    __tablename__ = "empresas"

    razon_social: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")

    usuarios: Mapped[list["Usuario"]] = relationship(back_populates="empresa", cascade="all,delete-orphan")
