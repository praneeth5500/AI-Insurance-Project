"""Matching engine: fit components, exclusions and immutable runs.

Adds what a run needs to explain itself after the fact
(docs/05_DATA_MODEL.md section 6, docs/06_RECOMMENDATION_ENGINE.md section 11):

* `fit_components` — the per-dimension label, its internal score and the
  evidence behind it;
* internal relevance and ordering on each candidate, which are stored for
  audit and never serialised to a client;
* a nullable `presentation_order`, because excluded candidates are recorded
  without being presented;
* `previous_run_id`, so a priority change links a new run to the one it
  replaced instead of rewriting it;
* `frozen_at`, and the removal of `updated_at` — a stored run is never
  updated, so a column implying otherwise is worse than no column.

The backfill defaults exist so this applies to a database that already holds
Phase 5 runs. Those runs predate the engine: they keep their recorded results
and get empty priorities and a zero exclusion count, which is accurate — the
prototype ordering excluded nothing.

Revision ID: fa6cc3b61cb4
Revises: 1957c83283c6
Create Date: 2026-08-25 21:53:16.527080
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "fa6cc3b61cb4"
down_revision: str | None = "1957c83283c6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "fit_components",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("candidate_id", sa.String(length=64), nullable=False),
        sa.Column("factor_key", sa.String(length=64), nullable=False),
        # Null means "no verified data". Distinct from 0, which would mean a
        # dimension was assessed and scored badly.
        sa.Column("normalized_score", sa.Float(), nullable=True),
        sa.Column("label", sa.String(length=24), nullable=False),
        sa.Column("user_priority_level", sa.String(length=16), nullable=False),
        sa.Column("hard_requirement", sa.Boolean(), nullable=False),
        sa.Column("evidence_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.ForeignKeyConstraint(
            ["candidate_id"], ["recommendation_candidates.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_fit_components_candidate", "fit_components", ["candidate_id"])

    op.add_column(
        "recommendation_candidates",
        sa.Column("product_version_id", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "recommendation_candidates",
        sa.Column(
            "exclusion_reasons_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.add_column(
        "recommendation_candidates",
        sa.Column("internal_relevance_value", sa.Float(), nullable=True),
    )
    op.add_column(
        "recommendation_candidates", sa.Column("internal_order", sa.Integer(), nullable=True)
    )
    op.alter_column(
        "recommendation_candidates",
        "presentation_order",
        existing_type=sa.INTEGER(),
        nullable=True,
    )
    op.create_foreign_key(
        "fk_recommendation_candidates_product_version",
        "recommendation_candidates",
        "product_versions",
        ["product_version_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.add_column(
        "recommendation_runs", sa.Column("previous_run_id", sa.String(length=64), nullable=True)
    )
    op.add_column(
        "recommendation_runs",
        sa.Column(
            "explanation_version",
            sa.String(length=64),
            nullable=False,
            server_default="pre-engine",
        ),
    )
    op.add_column(
        "recommendation_runs",
        sa.Column(
            "priorities_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.add_column(
        "recommendation_runs",
        sa.Column("excluded_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "recommendation_runs",
        sa.Column(
            "exclusion_reasons_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.add_column(
        "recommendation_runs",
        sa.Column(
            "frozen_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_foreign_key(
        "fk_recommendation_runs_previous_run",
        "recommendation_runs",
        "recommendation_runs",
        ["previous_run_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.drop_column("recommendation_runs", "updated_at")


def downgrade() -> None:
    op.add_column(
        "recommendation_runs",
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.drop_constraint(
        "fk_recommendation_runs_previous_run", "recommendation_runs", type_="foreignkey"
    )
    op.drop_column("recommendation_runs", "frozen_at")
    op.drop_column("recommendation_runs", "exclusion_reasons_json")
    op.drop_column("recommendation_runs", "excluded_count")
    op.drop_column("recommendation_runs", "priorities_json")
    op.drop_column("recommendation_runs", "explanation_version")
    op.drop_column("recommendation_runs", "previous_run_id")

    op.drop_constraint(
        "fk_recommendation_candidates_product_version",
        "recommendation_candidates",
        type_="foreignkey",
    )
    op.alter_column(
        "recommendation_candidates",
        "presentation_order",
        existing_type=sa.INTEGER(),
        nullable=False,
    )
    op.drop_column("recommendation_candidates", "internal_order")
    op.drop_column("recommendation_candidates", "internal_relevance_value")
    op.drop_column("recommendation_candidates", "exclusion_reasons_json")
    op.drop_column("recommendation_candidates", "product_version_id")

    op.drop_index("ix_fit_components_candidate", table_name="fit_components")
    op.drop_table("fit_components")
