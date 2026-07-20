"""Initial migration.

Revision ID: 20260512_0001
Revises:
Create Date: 2026-05-12 00:00:00
"""
from __future__ import annotations

from alembic import op
import pgvector.sqlalchemy
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260512_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    op.create_table(
        "empresas",
        sa.Column("razon_social", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("empresa_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["empresa_id"], ["empresas.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_empresas_empresa_id"), "empresas", ["empresa_id"], unique=False)
    op.create_index(op.f("ix_empresas_razon_social"), "empresas", ["razon_social"], unique=True)

    # op.create_table(
    #     "document_chunks",
    #     sa.Column("content", sa.Text(), nullable=False),
    #     sa.Column("metadata_json", sa.JSON(), nullable=False),
    #     sa.Column("embedding", pgvector.sqlalchemy.Vector(dim=1536), nullable=False),
    #     sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
    #     sa.Column("empresa_id", sa.Integer(), nullable=True),
    #     sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    #     sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    #     sa.ForeignKeyConstraint(["empresa_id"], ["empresas.id"], ondelete="SET NULL"),
    #     sa.PrimaryKeyConstraint("id"),
    # )
    # op.create_index(op.f("ix_document_chunks_empresa_id"), "document_chunks", ["empresa_id"], unique=False)

    op.create_table(
        "quality_reports_8d",
        sa.Column("titulo", sa.String(length=255), nullable=False),
        sa.Column("d2_problema", sa.Text(), nullable=False),
        sa.Column("d4_causa_raiz", sa.Text(), nullable=False),
        sa.Column("d5_acciones", sa.Text(), nullable=False),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("empresa_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["empresa_id"], ["empresas.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_quality_reports_8d_empresa_id"), "quality_reports_8d", ["empresa_id"], unique=False)

    op.create_table(
        "usuarios",
        sa.Column("empresa_id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("rol", sa.String(length=50), nullable=False),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["empresa_id"], ["empresas.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_usuarios_email"), "usuarios", ["email"], unique=True)
    op.create_index(op.f("ix_usuarios_empresa_id"), "usuarios", ["empresa_id"], unique=False)
    op.create_index(op.f("ix_usuarios_rol"), "usuarios", ["rol"], unique=False)

    op.create_table(
        "auditorias_ia",
        sa.Column("reporte_id", sa.Integer(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("hallazgos", sa.JSON(), nullable=False),
        sa.Column("aprobado", sa.Boolean(), nullable=False),
        sa.Column("raw_response", sa.Text(), nullable=False),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("empresa_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["empresa_id"], ["empresas.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["reporte_id"], ["quality_reports_8d.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_auditorias_ia_empresa_id"), "auditorias_ia", ["empresa_id"], unique=False)
    op.create_index(op.f("ix_auditorias_ia_reporte_id"), "auditorias_ia", ["reporte_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_auditorias_ia_reporte_id"), table_name="auditorias_ia")
    op.drop_index(op.f("ix_auditorias_ia_empresa_id"), table_name="auditorias_ia")
    op.drop_table("auditorias_ia")

    op.drop_index(op.f("ix_usuarios_rol"), table_name="usuarios")
    op.drop_index(op.f("ix_usuarios_empresa_id"), table_name="usuarios")
    op.drop_index(op.f("ix_usuarios_email"), table_name="usuarios")
    op.drop_table("usuarios")

    op.drop_index(op.f("ix_quality_reports_8d_empresa_id"), table_name="quality_reports_8d")
    op.drop_table("quality_reports_8d")

    # op.drop_index(op.f("ix_document_chunks_empresa_id"), table_name="document_chunks")
    # op.drop_table("document_chunks")

    op.drop_index(op.f("ix_empresas_razon_social"), table_name="empresas")
    op.drop_index(op.f("ix_empresas_empresa_id"), table_name="empresas")
    op.drop_table("empresas")
