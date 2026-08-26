"""Worker entrypoint.

Consumes the `PROCESS_POLICY` messages the API enqueues
(`docs/09_AWS_DEPLOYMENT.md` section 8) and runs each document through
extraction. The message carries identifiers only; the worker fetches the file
itself from private storage, so a queue row never becomes a second copy of
someone's policy.

The loop is deliberately plain: claim one job, run it, mark it, repeat. The
queue behind `JobQueue` is a database table today
(`docs/13_DECISIONS_AND_OPEN_ITEMS.md` open item 4) and can become SQS without
this file changing.

Two behaviours are worth stating outright:

* **A permanent failure is not retried.** A password-protected PDF will still
  be password-protected on the third attempt, and retrying only delays telling
  the reader something they could act on now.
* **Nothing about the document is logged.** Not its text, not its filename,
  not an exception's message. That is why `ExtractionFailed` carries a named
  reason rather than a string (`docs/09_AWS_DEPLOYMENT.md` section 9).
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import signal
import uuid

from app.core.config import Settings, get_settings
from app.core.logging import configure_logging, log_fields
from app.db.session import dispose_engine, get_session, init_engine
from app.extraction.pipeline import is_permanent, process_document
from app.extraction.text import ExtractionFailed
from app.jobs.models import JOB_PROCESS_POLICY
from app.jobs.queue import DatabaseJobQueue
from app.policies.storage import build_file_storage

logger = logging.getLogger(__name__)

#: How long to wait when the queue is empty. Long enough not to spin, short
#: enough that an upload does not sit visibly idle.
IDLE_SLEEP_SECONDS = 2.0


class Shutdown:
    """Cooperative stop, so a running job finishes before the process exits."""

    def __init__(self) -> None:
        self.requested = False

    def request(self, *_: object) -> None:
        self.requested = True


async def process_once(settings: Settings, *, worker_id: str) -> bool:
    """Claim and run at most one job. Returns whether there was work."""
    storage = build_file_storage(settings)

    async for db in get_session():
        queue = DatabaseJobQueue(db)
        job = await queue.claim(worker_id=worker_id)
        if job is None:
            await db.commit()
            return False

        # The claim is committed before the work starts, so a crash mid-job
        # leaves a claimed row whose lease expires rather than one another
        # worker picks up immediately and runs twice.
        await db.commit()

        if job.job_type != JOB_PROCESS_POLICY:
            await queue.fail(job_id=job.id, error=f"Unknown job type: {job.job_type}", retry=False)
            await db.commit()
            return True

        policy_id = str(job.payload.get("policyId", ""))
        document_id = str(job.payload.get("documentId", ""))

        try:
            await process_document(
                db, policy_id=policy_id, document_id=document_id, storage=storage
            )
        except ExtractionFailed as failure:
            # process_document has already recorded the failure against the
            # policy and committed it; the job only needs its own outcome.
            await queue.fail(
                job_id=job.id, error=failure.reason, retry=not is_permanent(failure.reason)
            )
            await db.commit()
            logger.info(
                "policy_job_failed",
                extra=log_fields(
                    event="policy_job_failed",
                    resource_type="uploaded_policy",
                    resource_id=policy_id,
                ),
            )
            return True
        except Exception:
            # Anything unexpected is retried. The exception is logged without
            # any identifier of the document's contents travelling with it.
            await db.rollback()
            await queue.fail(job_id=job.id, error="UNEXPECTED_ERROR", retry=True)
            await db.commit()
            logger.exception(
                "policy_job_error",
                extra=log_fields(
                    event="policy_job_error",
                    resource_type="uploaded_policy",
                    resource_id=policy_id,
                ),
            )
            return True

        await queue.succeed(job_id=job.id)
        await db.commit()
        logger.info(
            "policy_job_completed",
            extra=log_fields(
                event="policy_job_completed",
                resource_type="uploaded_policy",
                resource_id=policy_id,
            ),
        )
        return True

    return False


async def consume(settings: Settings, *, stop: Shutdown, max_jobs: int | None = None) -> int:
    """Run until asked to stop, or until `max_jobs` jobs have been handled.

    Owns the database engine for the life of the loop, and disposes of it on
    the way out — a worker that leaves connections behind exhausts the pool
    the API needs.
    """
    init_engine(settings)
    try:
        return await _loop(stop=stop, max_jobs=max_jobs, settings=settings)
    finally:
        await dispose_engine()


async def _loop(*, stop: Shutdown, max_jobs: int | None, settings: Settings) -> int:
    worker_id = f"{os.getpid()}-{uuid.uuid4().hex[:8]}"
    handled = 0

    while not stop.requested:
        did_work = await process_once(settings, worker_id=worker_id)
        if did_work:
            handled += 1
            if max_jobs is not None and handled >= max_jobs:
                break
            continue
        if max_jobs is not None:
            break
        await asyncio.sleep(IDLE_SLEEP_SECONDS)

    return handled


def run(settings: Settings | None = None, *, max_jobs: int | None = None) -> int:
    """Start the worker. Returns the process exit code."""
    settings = settings or get_settings()
    settings.validate_for_environment()
    configure_logging(settings.log_level)

    stop = Shutdown()
    with contextlib.suppress(ValueError):
        # Signal handlers can only be installed on the main thread; tests call
        # `consume` directly and do not need them.
        signal.signal(signal.SIGTERM, stop.request)
        signal.signal(signal.SIGINT, stop.request)

    logger.info("worker_started", extra=log_fields(event="worker_started"))
    asyncio.run(consume(settings, stop=stop, max_jobs=max_jobs))
    logger.info("worker_stopped", extra=log_fields(event="worker_stopped"))
    return 0


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
