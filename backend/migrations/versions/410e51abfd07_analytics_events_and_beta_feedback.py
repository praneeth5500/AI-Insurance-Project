"""Analytics events and beta feedback.

feedback is from docs/05_DATA_MODEL.md section 10.

analytics_events is not in the data model — analytics usually goes to a
third-party product and no vendor is chosen, so events are written here behind
a sink interface. That keeps the beta's data in the beta's database and leaves
the vendor decision open (docs/SPEC_ISSUES.md).

properties_json is not a free-form bag despite its type: only keys declared
for that event in app.analytics.events survive sanitisation, which is what
makes "no sensitive answers in analytics" a property of the system rather than
a promise (docs/03_FRONTEND_ARCHITECTURE.md section 7).

Revision ID: 410e51abfd07
Revises: 22d982908cde
Create Date: 2026-08-27 17:07:15.644628
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "410e51abfd07"
down_revision: str | None = "22d982908cde"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "analytics_events",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=True),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("properties_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_analytics_events_name", "analytics_events", ["name", "created_at"], unique=False
    )
    op.create_table(
        "feedback",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=64), nullable=True),
        sa.Column("context_type", sa.String(length=32), nullable=False),
        sa.Column("context_id", sa.String(length=64), nullable=True),
        sa.Column("rating", sa.Integer(), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_feedback_context", "feedback", ["context_type", "created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_feedback_context", table_name="feedback")
    op.drop_table("feedback")
    op.drop_index("ix_analytics_events_name", table_name="analytics_events")
    op.drop_table("analytics_events")
