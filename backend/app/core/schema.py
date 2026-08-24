"""Shared Pydantic base for API payloads.

docs/08_API_CONTRACTS.md uses camelCase on the wire (``runId``,
``questionnaireSessionId``); Python stays snake_case internally. Every request
and response model in the app should inherit from :class:`ApiModel` so that
boundary is applied in exactly one place.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class ApiModel(BaseModel):
    """Base model for anything crossing the HTTP boundary."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        extra="forbid",
    )
