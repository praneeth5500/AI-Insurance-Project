"""Email delivery.

The vendor is an open decision (docs/13_DECISIONS_AND_OPEN_ITEMS.md item 1),
so only the interface is fixed here. A production adapter — SES is the natural
fit for an AWS-centred stack — implements the same Protocol and is selected by
configuration, with no change to the auth service.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Protocol

from app.core.config import Settings
from app.core.logging import log_fields

logger = logging.getLogger(__name__)


class EmailProvider(Protocol):
    """Outbound email."""

    async def send_magic_link(self, *, email: str, link: str) -> None:
        """Deliver a sign-in link. Must never log the link or the address."""
        ...


class DevFileEmailProvider:
    """Local development adapter: writes the link to a file, not to the log.

    docs/09_AWS_DEPLOYMENT.md section 9 forbids magic-link tokens in logs, and
    that rule should not be bent just because it is inconvenient in
    development. The link goes to a gitignored file instead, so the application
    log stays clean and the developer still gets their link.

    Refuses to run outside `local` so it cannot silently swallow real invites.
    """

    def __init__(self, settings: Settings, path: Path | None = None) -> None:
        if not settings.is_local:
            raise RuntimeError(
                "DevFileEmailProvider is for APP_ENV=local only; "
                "configure a real email adapter for deployed environments."
            )
        self._path = path or Path(".dev-magic-links.log")

    async def send_magic_link(self, *, email: str, link: str) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("a", encoding="utf-8") as handle:
            handle.write(f"{email}\n  {link}\n\n")
        # The log records that delivery happened, never what was delivered.
        logger.info("magic_link_delivered", extra=log_fields(event="magic_link_delivered"))


def build_email_provider(settings: Settings) -> EmailProvider:
    """Select the adapter for this environment.

    Deployed environments deliberately fail closed: rather than silently not
    sending invites, the API refuses to start until an adapter is configured.
    """
    if settings.is_local:
        return DevFileEmailProvider(settings)
    raise RuntimeError(
        "No production email provider is configured. "
        "Implement an EmailProvider adapter (for example AWS SES) and select it here "
        "before deploying; the auth flow cannot deliver invites without one."
    )
