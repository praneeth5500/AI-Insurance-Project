"""Uploaded policies, their documents, and the processing queue.

docs/05_DATA_MODEL.md section 7 and docs/09_AWS_DEPLOYMENT.md section 8.

Three things worth noting about the shape:

* `policy_documents` stores a storage *key*, never the bytes. The document
  itself lives in object storage and is only ever streamed back through an
  authenticated route.
* `processing_jobs.payload_json` carries identifiers only. A queue row must
  never become a second, unprotected copy of someone's policy.
* `policy_deletion_audits` records that a deletion happened and whether the
  objects were confirmed gone, while holding nothing about the document
  itself — a delete that leaves no trace cannot be shown to work, and a trace
  that keeps the content would defeat the deletion.

Revision ID: 03224932f46f
Revises: fa6cc3b61cb4
Create Date: 2026-08-26 22:34:25.739973
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "03224932f46f"
down_revision: str | None = "fa6cc3b61cb4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "policy_deletion_audits",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("policy_id", sa.String(length=64), nullable=False),
        sa.Column("documents_removed", sa.Integer(), nullable=False),
        sa.Column("storage_confirmed", sa.Boolean(), nullable=False),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_policy_deletion_audits_user", "policy_deletion_audits", ["user_id"], unique=False
    )
    op.create_table(
        "uploaded_policies",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("domain", sa.String(length=16), nullable=True),
        sa.Column("display_name", sa.String(length=200), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("failure_reason", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("ready_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_uploaded_policies_user", "uploaded_policies", ["user_id", "created_at"], unique=False
    )
    op.create_table(
        "policy_documents",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("policy_id", sa.String(length=64), nullable=False),
        sa.Column("storage_key", sa.String(length=512), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("mime_type", sa.String(length=64), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column("is_encrypted", sa.Boolean(), nullable=False),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["policy_id"], ["uploaded_policies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_policy_documents_policy", "policy_documents", ["policy_id"], unique=False)
    op.create_table(
        "processing_jobs",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("job_type", sa.String(length=32), nullable=False),
        sa.Column("payload_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("claimed_by", sa.String(length=64), nullable=True),
        sa.Column(
            "available_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("policy_id", sa.String(length=64), nullable=True),
        sa.ForeignKeyConstraint(["policy_id"], ["uploaded_policies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_processing_jobs_claimable", "processing_jobs", ["status", "available_at"], unique=False
    )
    op.create_index("ix_processing_jobs_policy", "processing_jobs", ["policy_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_processing_jobs_policy", table_name="processing_jobs")
    op.drop_index("ix_processing_jobs_claimable", table_name="processing_jobs")
    op.drop_table("processing_jobs")
    op.drop_index("ix_policy_documents_policy", table_name="policy_documents")
    op.drop_table("policy_documents")
    op.drop_index("ix_uploaded_policies_user", table_name="uploaded_policies")
    op.drop_table("uploaded_policies")
    op.drop_index("ix_policy_deletion_audits_user", table_name="policy_deletion_audits")
    op.drop_table("policy_deletion_audits")
