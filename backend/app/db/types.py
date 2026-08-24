"""Shared column conventions."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime
from sqlalchemy.orm import Mapped, mapped_column


def new_id(prefix: str) -> str:
    """Prefixed identifier, e.g. `usr_9f2c...`.

    docs/08_API_CONTRACTS.md shows prefixed ids (`usr_`, `rr_`, `pol_`), which
    make it obvious in a log or a bug report what kind of thing an id refers to.
    """
    return f"{prefix}_{uuid.uuid4().hex}"


def utcnow() -> datetime:
    return datetime.now(UTC)


def timestamp_column(**kwargs: object) -> Mapped[datetime]:
    """A timezone-aware timestamp. Naive datetimes are a source of subtle bugs."""
    return mapped_column(DateTime(timezone=True), **kwargs)  # type: ignore[arg-type]
