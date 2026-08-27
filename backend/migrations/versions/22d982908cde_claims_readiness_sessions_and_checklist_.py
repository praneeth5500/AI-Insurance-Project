"""Claims readiness sessions and checklist items.

docs/05_DATA_MODEL.md section 9.

claims_checklist_items.origin is the column that keeps this honest.
docs/07_POLICY_DECODER_AI.md section 10 requires the three kinds of item to
stay apart — a requirement read from this policy, a general suggestion from an
approved template, and a question only the insurer can answer — and says "do
not blend them". source_clause_id is set only on the first kind: an item
claiming to come from the policy without a clause behind it would be the
invention that separation exists to prevent.

Revision ID: 22d982908cde
Revises: 363c3aea1b14
Create Date: 2026-08-27 16:51:57.649298
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "22d982908cde"
down_revision: str | None = "363c3aea1b14"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "claims_readiness_sessions",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("policy_id", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["policy_id"], ["uploaded_policies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_claims_sessions_user",
        "claims_readiness_sessions",
        ["user_id", "policy_id"],
        unique=False,
    )
    op.create_table(
        "claims_checklist_items",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("session_id", sa.String(length=64), nullable=False),
        sa.Column("item_key", sa.String(length=64), nullable=False),
        sa.Column("label", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("origin", sa.String(length=32), nullable=False),
        sa.Column("source_clause_id", sa.String(length=64), nullable=True),
        sa.Column("source_page", sa.Integer(), nullable=True),
        sa.Column("completed", sa.Boolean(), nullable=False),
        sa.Column("user_note", sa.Text(), nullable=True),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["session_id"], ["claims_readiness_sessions.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["source_clause_id"], ["policy_clauses.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_claims_items_session", "claims_checklist_items", ["session_id", "ordinal"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_claims_items_session", table_name="claims_checklist_items")
    op.drop_table("claims_checklist_items")
    op.drop_index("ix_claims_sessions_user", table_name="claims_readiness_sessions")
    op.drop_table("claims_readiness_sessions")
