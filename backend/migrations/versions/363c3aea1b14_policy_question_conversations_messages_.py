"""Conversations, messages and citations for policy Q&A.

docs/05_DATA_MODEL.md section 8.

conversations.policy_id is NOT NULL on purpose: a conversation without a
policy would be a general chat surface, and docs/01_PRODUCT_SPEC.md section 5
keeps Q&A inside policy context.

messages.ordinal exists because created_at defaults to now(), which in
PostgreSQL is transaction start time — a question and the answer written in
the same transaction share a timestamp and cannot be ordered by it.

Message content is the reader's question and our answer about their own
policy. Like page text, it lives here and nowhere else — never in a log,
never in analytics (docs/09_AWS_DEPLOYMENT.md section 9).

Revision ID: 363c3aea1b14
Revises: ff43ed2f4986
Create Date: 2026-08-26 23:13:16.137881
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "363c3aea1b14"
down_revision: str | None = "ff43ed2f4986"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "conversations",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("policy_id", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["policy_id"], ["uploaded_policies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_conversations_policy", "conversations", ["policy_id", "user_id"], unique=False
    )
    op.create_table(
        "messages",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("conversation_id", sa.String(length=64), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("answer_state", sa.String(length=32), nullable=True),
        sa.Column("model_metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_messages_conversation", "messages", ["conversation_id", "ordinal"], unique=False
    )
    op.create_table(
        "citations",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("message_id", sa.String(length=64), nullable=False),
        sa.Column("policy_clause_id", sa.String(length=64), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("quote_start", sa.Integer(), nullable=True),
        sa.Column("quote_end", sa.Integer(), nullable=True),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["message_id"], ["messages.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["policy_clause_id"], ["policy_clauses.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_citations_message", "citations", ["message_id", "ordinal"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_citations_message", table_name="citations")
    op.drop_table("citations")
    op.drop_index("ix_messages_conversation", table_name="messages")
    op.drop_table("messages")
    op.drop_index("ix_conversations_policy", table_name="conversations")
    op.drop_table("conversations")
