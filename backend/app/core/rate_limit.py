"""Rate limiting.

`docs/11_BUILD_PLAN.md` Phase 16 lists rate limits among the things to review
before a beta, and `docs/PHASE_2_NOTES.md` has carried "the magic-link endpoint
is unthrottled" as an open item since authentication was built. This closes it.

## What is actually at risk

Not much of this product is expensive to call. Two things are:

* **`request-magic-link`.** Unthrottled, it lets anyone send unlimited sign-in
  emails to an allowlisted address — an email bomb aimed at a beta user, using
  our sender. It also generates unbounded tokens.
* **`verify`.** A token is 32 bytes of entropy so guessing is not the concern;
  volume is. Throttling it keeps a stolen-token search from being free.

Uploads and questions are limited too, because both do real work per request:
one parses a PDF, the other scans every clause.

## The window

A fixed-size sliding window over timestamps, per key. Simple enough to reason
about, and exact rather than approximate — a token bucket would let a burst
through that a beta does not need to allow.

## The honest limitation

This is **per process**. Two API instances mean two independent windows, so the
effective limit doubles. For a friends-and-family beta on one container that is
adequate, and the interface is small enough that a shared store slots in
without touching call sites. It must not ship to anything horizontally scaled
without that swap — recorded in `docs/PHASE_16_NOTES.md`.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass


@dataclass(frozen=True)
class Limit:
    """How many times a key may be used within a window."""

    times: int
    seconds: int

    def __post_init__(self) -> None:
        if self.times < 1 or self.seconds < 1:
            raise ValueError("A limit needs a positive count and window.")


#: Per-email, so one address cannot be flooded with sign-in mail.
MAGIC_LINK_PER_EMAIL = Limit(times=5, seconds=15 * 60)
#: Per-IP, so one source cannot spray many addresses.
MAGIC_LINK_PER_IP = Limit(times=20, seconds=15 * 60)
#: Volume, not guessing: a token carries 32 bytes of entropy.
VERIFY_PER_IP = Limit(times=30, seconds=15 * 60)
#: Each upload parses a PDF.
UPLOAD_PER_USER = Limit(times=20, seconds=60 * 60)
#: Each question scans every clause of a policy.
QUESTION_PER_USER = Limit(times=60, seconds=60 * 60)


class RateLimiter:
    """A sliding-window limiter, safe to call from several threads."""

    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, key: str, limit: Limit, *, now: float | None = None) -> bool:
        """Record an attempt. Returns False when the limit is already spent.

        The attempt is recorded only when it is allowed, so a client that is
        being refused does not push its own window further out — otherwise a
        caller hammering the endpoint would never recover.
        """
        moment = now if now is not None else time.monotonic()
        cutoff = moment - limit.seconds

        with self._lock:
            hits = self._hits[key]
            while hits and hits[0] <= cutoff:
                hits.popleft()

            if len(hits) >= limit.times:
                return False

            hits.append(moment)
            return True

    def reset(self, key: str | None = None) -> None:
        """Clear one key, or everything. For tests and for support."""
        with self._lock:
            if key is None:
                self._hits.clear()
            else:
                self._hits.pop(key, None)


#: One limiter for the process. Module-level because the window has to be
#: shared across requests, which is the entire point.
limiter = RateLimiter()


def client_ip(request: object) -> str:
    """The caller's address, as well as it can be known.

    Behind a load balancer the socket address is the balancer's, so
    `X-Forwarded-For`'s first entry is used when present. That header is
    client-controllable when nothing strips it, which is why it is only ever
    used as a rate-limit *key*: a forged value costs the forger their own
    bucket and buys them nothing.
    """
    headers = getattr(request, "headers", {})
    forwarded = headers.get("x-forwarded-for") if hasattr(headers, "get") else None
    if forwarded:
        return str(forwarded).split(",")[0].strip()[:64]
    client = getattr(request, "client", None)
    host = getattr(client, "host", None)
    return str(host) if host else "unknown"
