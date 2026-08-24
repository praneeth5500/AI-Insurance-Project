"""Apply BETA_ALLOWLIST_EMAILS to the database.

    make seed-allowlist

Idempotent: running it twice invites nobody twice. Addresses are printed back
to the operator who supplied them, but never written to the application log.
"""

from __future__ import annotations

import asyncio
import sys

from app.auth.allowlist import seed_allowlist
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.session import dispose_engine, init_engine


async def main() -> int:
    settings = get_settings()
    configure_logging(settings.log_level)

    emails = settings.allowlist_seed_emails
    if not emails:
        print("BETA_ALLOWLIST_EMAILS is empty; nothing to do.")
        print("Set it in .env, e.g. BETA_ALLOWLIST_EMAILS=you@example.com,friend@example.com")
        return 1

    init_engine(settings)
    try:
        from app.db.session import get_session

        agen = get_session()
        db = await anext(agen)
        try:
            result = await seed_allowlist(db, emails)
        finally:
            await agen.aclose()
    finally:
        await dispose_engine()

    print(f"Invited: {result.invited}")
    print(f"Already invited: {result.already_invited}")
    print(f"Reinstated: {result.reinstated}")
    for email in emails:
        print(f"  - {email}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
