"""Enqueuing and claiming background work.

The interface is deliberately small — enqueue, claim, complete, fail — because
that is all SQS offers too, and an interface shaped around a database table
would not survive the move.

Claiming is the part worth reading. `SELECT ... FOR UPDATE SKIP LOCKED` lets
several workers pull from the same queue without handing the same job to two
of them and without blocking each other. A claim also has a lease: a worker
that dies mid-job leaves a row that another worker can take once the lease
expires, instead of a job that is RUNNING forever.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Protocol

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.types import utcnow
from app.jobs.models import (
    JOB_FAILED,
    JOB_QUEUED,
    JOB_RUNNING,
    JOB_SUCCEEDED,
    ProcessingJob,
)

#: How long a claim is honoured before another worker may take the job. Long
#: enough for a slow OCR pass, short enough that a crash is not fatal.
DEFAULT_LEASE = timedelta(minutes=15)


@dataclass(frozen=True)
class ClaimedJob:
    id: str
    job_type: str
    payload: dict[str, Any]
    attempts: int


class JobQueue(Protocol):
    async def enqueue(
        self, *, job_type: str, payload: dict[str, Any], policy_id: str | None = None
    ) -> str: ...

    async def claim(self, *, worker_id: str) -> ClaimedJob | None: ...

    async def succeed(self, *, job_id: str) -> None: ...

    async def fail(self, *, job_id: str, error: str, retry: bool = True) -> None: ...


class DatabaseJobQueue:
    """The local adapter (open item 4).

    Every method takes the session from the caller rather than opening its
    own, so enqueuing a job and writing the record that job is about happen in
    one transaction. A job that references a policy row that was rolled back
    would be a job the worker can only fail.
    """

    def __init__(self, db: AsyncSession, *, lease: timedelta = DEFAULT_LEASE) -> None:
        self._db = db
        self._lease = lease

    async def enqueue(
        self, *, job_type: str, payload: dict[str, Any], policy_id: str | None = None
    ) -> str:
        job = ProcessingJob(
            job_type=job_type,
            payload_json=payload,
            policy_id=policy_id,
            status=JOB_QUEUED,
        )
        self._db.add(job)
        await self._db.flush()
        return job.id

    async def claim(self, *, worker_id: str) -> ClaimedJob | None:
        """Take one job, or return None if there is nothing to do."""
        now = utcnow()
        lease_cutoff = now - self._lease

        candidate = (
            await self._db.execute(
                select(ProcessingJob)
                .where(
                    ProcessingJob.available_at <= now,
                    (ProcessingJob.status == JOB_QUEUED)
                    # A RUNNING job whose lease expired is available again:
                    # the worker holding it is gone.
                    | (
                        (ProcessingJob.status == JOB_RUNNING)
                        & (ProcessingJob.claimed_at < lease_cutoff)
                    ),
                )
                .order_by(ProcessingJob.available_at)
                .limit(1)
                .with_for_update(skip_locked=True)
            )
        ).scalar_one_or_none()

        if candidate is None:
            return None

        candidate.status = JOB_RUNNING
        candidate.claimed_at = now
        candidate.claimed_by = worker_id
        candidate.attempts += 1
        await self._db.flush()

        return ClaimedJob(
            id=candidate.id,
            job_type=candidate.job_type,
            payload=dict(candidate.payload_json),
            attempts=candidate.attempts,
        )

    async def succeed(self, *, job_id: str) -> None:
        await self._db.execute(
            update(ProcessingJob)
            .where(ProcessingJob.id == job_id)
            .values(
                status=JOB_SUCCEEDED,
                completed_at=utcnow(),
                claimed_at=None,
                claimed_by=None,
                last_error=None,
            )
        )

    async def fail(self, *, job_id: str, error: str, retry: bool = True) -> None:
        """Record a failure, and retry only while attempts remain.

        A job that has run out of attempts stays FAILED so the policy it
        belongs to can be shown as failed. `docs/02_UX_UI_SPEC.md` section 14:
        say clearly what failed. A job that quietly retried forever would
        leave the reader watching a spinner instead.
        """
        job = (
            await self._db.execute(select(ProcessingJob).where(ProcessingJob.id == job_id))
        ).scalar_one_or_none()
        if job is None:
            return

        job.last_error = error[:2000]
        job.claimed_at = None
        job.claimed_by = None

        if retry and job.attempts < job.max_attempts:
            job.status = JOB_QUEUED
            # Linear backoff. Enough to ride out a transient dependency
            # without making a genuinely broken document take an hour to fail.
            job.available_at = utcnow() + timedelta(seconds=30 * job.attempts)
        else:
            job.status = JOB_FAILED
            job.completed_at = utcnow()
