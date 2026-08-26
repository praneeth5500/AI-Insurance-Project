"""Request-scoped wiring for the upload flow."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.auth.dependencies import AppSettings, DbSession
from app.jobs.queue import DatabaseJobQueue, JobQueue
from app.policies.errors import PolicyDecoderDisabledError
from app.policies.storage import FileStorage, build_file_storage


def require_decoder_enabled(settings: AppSettings) -> None:
    """Refuse the whole feature while it is switched off.

    The flag is checked on the server, not only hidden in the UI. An upload
    endpoint that quietly worked while the product said the feature did not
    exist would accept people's policy documents with nothing to do with them
    (`docs/12_BETA_CHECKLIST.md`: no dead buttons; `CLAUDE.md` rule 8: never
    make a UI claim the backend cannot support — and the inverse holds too).
    """
    if not settings.feature_policy_decoder:
        raise PolicyDecoderDisabledError


def get_storage(settings: AppSettings) -> FileStorage:
    return build_file_storage(settings)


def get_queue(db: DbSession) -> JobQueue:
    """Share the request's session, so enqueuing is part of its transaction."""
    return DatabaseJobQueue(db)


Storage = Annotated[FileStorage, Depends(get_storage)]
Queue = Annotated[JobQueue, Depends(get_queue)]
DecoderEnabled = Depends(require_decoder_enabled)
