"""Add module key metadata index for document chunks.

Revision ID: 20260513_0003
Revises: 20260512_0002
Create Date: 2026-05-13 00:00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260513_0003"
down_revision = "20260512_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE document_chunks
        SET metadata_json = (metadata_json::jsonb || '{"module_key": "general"}'::jsonb)::json
        WHERE metadata_json->>'module_key' IS NULL;
        """
    )
    op.create_index(
        "ix_document_chunks_empresa_module",
        "document_chunks",
        [
            sa.text("(metadata_json->>'empresa_id')"),
            sa.text("(metadata_json->>'module_key')"),
        ],
    )


def downgrade() -> None:
    op.drop_index("ix_document_chunks_empresa_module", table_name="document_chunks")
