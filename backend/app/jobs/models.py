"""The local job queue table.

`docs/09_AWS_DEPLOYMENT.md` section 8 makes document processing asynchronous
and says a message carries *identifiers, not raw PDF content* — the worker
fetches the file itself, through an authorised path. That rule is what this
table exists to hold: the payload here is ids and nothing else, so a queue
row can never become a second, unprotected copy of someone's policy.

`docs/13_DECISIONS_AND_OPEN_ITEMS.md` open item 4 leaves the queue
implementation undecided and says a local adapter is still needed either way.
This is that adapter. It is a real queue — claims are atomic, work is retried,
failures are recorded — but it is a database table, and a production beta
should move to SQS behind the same interface.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import new_id, timestamp_column

#: The only job type so far. Named rather than free-form so an unknown type is
#: a visible error instead of a silently ignored row.
JOB_PROCESS_POLICY = "PROCESS_POLICY"

JOB_QUEUED = "QUEUED"
JOB_RUNNING = "RUNNING"
JOB_SUCCEEDED = "SUCCEEDED"
JOB_FAILED = "FAILED"


class ProcessingJob(Base):
    __tablename__ = "processing_jobs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: new_id("job"))
    job_type: Mapped[str] = mapped_column(String(32), nullable=False)
    #: Identifiers only — never document bytes, never extracted text.
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default=JOB_QUEUED)

    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=3)

    #: Why the last attempt failed. Plain text, written by us — never the raw
    #: contents of a document (docs/09_AWS_DEPLOYMENT.md section 9).
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    #: Set while a worker holds the job, so a crashed worker's claim can be
    #: reclaimed rather than blocking the queue forever.
    claimed_at: Mapped[datetime | None] = timestamp_column(nullable=True)
    claimed_by: Mapped[str | None] = mapped_column(String(64), nullable=True)

    available_at: Mapped[datetime] = timestamp_column(nullable=False, server_default=func.now())
    created_at: Mapped[datetime] = timestamp_column(nullable=False, server_default=func.now())
    completed_at: Mapped[datetime | None] = timestamp_column(nullable=True)

    #: The policy this job is about, so a policy's processing state can be
    #: found without scanning payloads.
    policy_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("uploaded_policies.id", ondelete="CASCADE"), nullable=True
    )

    __table_args__ = (
        Index("ix_processing_jobs_claimable", "status", "available_at"),
        Index("ix_processing_jobs_policy", "policy_id"),
    )
