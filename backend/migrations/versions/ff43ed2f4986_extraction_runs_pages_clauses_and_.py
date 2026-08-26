"""Extraction runs, pages, clauses and policy facts.

docs/05_DATA_MODEL.md section 7 and docs/07_POLICY_DECODER_AI.md section 3's
three-layer truth model. The source layer (pages, clauses) and the structured
fact layer (policy_facts) are separate tables on purpose: a fact points at the
clause that supports it, so a value can always be traced back to wording the
reader can read for themselves.

policy_facts carries confidence twice — a number and a state — because
docs/07_POLICY_DECODER_AI.md shows it both ways (docs/SPEC_ISSUES.md issue 2).
The state is derived from the number and is what the UI reasons about.

Page text lives in policy_pages and nowhere else: not in a queue payload, not
in an error message, not in a log (docs/09_AWS_DEPLOYMENT.md section 9).

Revision ID: ff43ed2f4986
Revises: 03224932f46f
Create Date: 2026-08-26 22:50:00.491880
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "ff43ed2f4986"
down_revision: str | None = "03224932f46f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "extraction_runs",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("policy_id", sa.String(length=64), nullable=False),
        sa.Column("schema_version", sa.String(length=32), nullable=False),
        sa.Column("ocr_provider", sa.String(length=64), nullable=True),
        sa.Column("ai_provider", sa.String(length=64), nullable=True),
        sa.Column("model", sa.String(length=128), nullable=True),
        sa.Column("prompt_version", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("failure_reason", sa.String(length=64), nullable=True),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["policy_id"], ["uploaded_policies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_extraction_runs_policy", "extraction_runs", ["policy_id"], unique=False)
    op.create_table(
        "policy_clauses",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("policy_id", sa.String(length=64), nullable=False),
        sa.Column("document_id", sa.String(length=64), nullable=False),
        sa.Column("clause_type", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=True),
        sa.Column("source_page", sa.Integer(), nullable=False),
        sa.Column("source_text", sa.Text(), nullable=False),
        sa.Column("normalized_text", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["policy_documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["policy_id"], ["uploaded_policies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_policy_clauses_policy", "policy_clauses", ["policy_id", "ordinal"], unique=False
    )
    op.create_table(
        "policy_pages",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("document_id", sa.String(length=64), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("extraction_method", sa.String(length=16), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(["document_id"], ["policy_documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_policy_pages_document", "policy_pages", ["document_id", "page_number"], unique=True
    )
    op.create_table(
        "policy_facts",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("policy_id", sa.String(length=64), nullable=False),
        sa.Column("extraction_run_id", sa.String(length=64), nullable=False),
        sa.Column("fact_key", sa.String(length=64), nullable=False),
        sa.Column("value_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("confidence_state", sa.String(length=16), nullable=False),
        sa.Column("clause_id", sa.String(length=64), nullable=True),
        sa.Column("source_page", sa.Integer(), nullable=True),
        sa.Column("source_quote", sa.Text(), nullable=True),
        sa.Column("alternatives_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["clause_id"], ["policy_clauses.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["extraction_run_id"], ["extraction_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["policy_id"], ["uploaded_policies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_policy_facts_policy", "policy_facts", ["policy_id", "fact_key"], unique=False
    )
    op.create_index("ix_policy_facts_run", "policy_facts", ["extraction_run_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_policy_facts_run", table_name="policy_facts")
    op.drop_index("ix_policy_facts_policy", table_name="policy_facts")
    op.drop_table("policy_facts")
    op.drop_index("ix_policy_pages_document", table_name="policy_pages")
    op.drop_table("policy_pages")
    op.drop_index("ix_policy_clauses_policy", table_name="policy_clauses")
    op.drop_table("policy_clauses")
    op.drop_index("ix_extraction_runs_policy", table_name="extraction_runs")
    op.drop_table("extraction_runs")
