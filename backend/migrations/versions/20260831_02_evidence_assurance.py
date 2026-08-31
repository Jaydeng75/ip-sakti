"""evidence assurance retrieval, jobs and source monitoring

Revision ID: 20260831_02
Revises: 20260831_01
Create Date: 2026-08-31
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision: str = "20260831_02"
down_revision: str | None = "20260831_01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    postgres = bind.dialect.name == "postgresql"
    if postgres:
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    vector_type = Vector(384) if postgres else sa.JSON()
    with op.batch_alter_table("evidence_chunks") as batch:
        batch.add_column(sa.Column("embedding_vector", vector_type, nullable=True))
        batch.add_column(sa.Column("embedding_provider", sa.String(length=60), server_default="deterministic", nullable=False))
        batch.add_column(sa.Column("embedding_model", sa.String(length=180), server_default="blake2b-feature-hash", nullable=False))
        batch.add_column(sa.Column("embedding_revision", sa.String(length=100), server_default="v1", nullable=False))
    if postgres:
        op.execute(
            "CREATE INDEX ix_evidence_chunks_embedding_hnsw ON evidence_chunks "
            "USING hnsw (embedding_vector vector_cosine_ops) WHERE embedding_vector IS NOT NULL"
        )

    op.create_table(
        "reindex_jobs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("case_id", sa.Integer(), sa.ForeignKey("innovation_cases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("requested_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(length=30), server_default="queued", nullable=False),
        sa.Column("embedding_model", sa.String(length=180), nullable=False),
        sa.Column("embedding_revision", sa.String(length=100), nullable=False),
        sa.Column("result", sa.JSON(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_reindex_jobs_case_id", "reindex_jobs", ["case_id"])
    op.create_index("ix_reindex_jobs_requested_by", "reindex_jobs", ["requested_by"])
    op.create_index("ix_reindex_jobs_status", "reindex_jobs", ["status"])

    op.create_table(
        "source_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_id", sa.String(length=120), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("content_sha256", sa.String(length=64), nullable=True),
        sa.Column("etag", sa.String(length=255), nullable=True),
        sa.Column("last_modified", sa.String(length=255), nullable=True),
        sa.Column("http_status", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=40), server_default="unchecked", nullable=False),
        sa.Column("change_summary", sa.JSON(), nullable=False),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_source_snapshots_source_id", "source_snapshots", ["source_id"])
    op.create_index("ix_source_snapshots_status", "source_snapshots", ["status"])
    op.create_index("ix_source_snapshots_checked_at", "source_snapshots", ["checked_at"])


def downgrade() -> None:
    op.drop_table("source_snapshots")
    op.drop_table("reindex_jobs")
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP INDEX IF EXISTS ix_evidence_chunks_embedding_hnsw")
    with op.batch_alter_table("evidence_chunks") as batch:
        batch.drop_column("embedding_revision")
        batch.drop_column("embedding_model")
        batch.drop_column("embedding_provider")
        batch.drop_column("embedding_vector")
