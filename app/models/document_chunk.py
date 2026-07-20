from __future__ import annotations

from sqlalchemy import JSON, Text
from sqlalchemy.orm import Mapped, mapped_column
from pgvector.sqlalchemy import Vector

from app.models.base import Base, TenantAuditMixin


class DocumentChunk(TenantAuditMixin, Base):
    __tablename__ = "document_chunks"

    content: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    embedding: Mapped[list[float]] = mapped_column(Vector(1536), nullable=False)

