"""Declarative base for ORM models.

Phase 0 intentionally defines no tables. docs/05_DATA_MODEL.md is a *logical*
model and says migrations should only be generated after the relationships are
validated in implementation, so domain models arrive with the phases that need
them (Phase 2 onwards).
"""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class every ORM model will inherit from."""
