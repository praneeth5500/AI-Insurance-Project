"""Worker entrypoint.

Phase 0 deliberately ships a *placeholder*. The queue technology is an open
item (docs/13_DECISIONS_AND_OPEN_ITEMS.md item 4), so no queue adapter is
implemented here — inventing one now would be a guess, not a decision.

What this process does today:

* load and validate the same settings the API uses;
* configure the same safe structured logging;
* report that it started, then exit cleanly.

Phase 10 replaces :func:`run` with a real consume loop that receives the
``{"job_type": "PROCESS_POLICY", "policy_id": ..., "document_id": ...}``
message described in docs/09_AWS_DEPLOYMENT.md section 8. Messages carry
identifiers only; the worker fetches the file itself.
"""

from __future__ import annotations

import logging

from app.core.config import Settings, get_settings
from app.core.logging import configure_logging, log_fields

logger = logging.getLogger(__name__)


def run(settings: Settings | None = None) -> int:
    """Start the worker. Returns the process exit code."""
    settings = settings or get_settings()
    settings.validate_for_environment()
    configure_logging(settings.log_level)

    logger.info("worker_started", extra=log_fields(event="worker_started"))
    logger.info(
        "worker_idle_no_queue_configured",
        extra=log_fields(event="worker_idle_no_queue_configured"),
    )
    logger.info("worker_stopped", extra=log_fields(event="worker_stopped"))
    return 0


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
