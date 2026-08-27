"""Analytics payloads.

A client may only post events marked `client_emittable`, and only the
properties those events declare. Both checks happen on the server: a browser
is not a trusted source of funnel data, and an endpoint that accepted any
name with any properties would be an unbounded write with a friendly name.
"""

from __future__ import annotations

from typing import Any

from app.core.schema import ApiModel


class TrackEventRequest(ApiModel):
    name: str
    properties: dict[str, Any] = {}


class TrackEventResponse(ApiModel):
    recorded: bool
