"""Withdraw beta access from one or more addresses.

    make revoke-access EMAILS=someone@example.com,another@example.com

Ends every live session as well as clearing the allowlist flag, so access
stops now rather than whenever the session cookie happens to expire.

Addresses are printed back to the operator who supplied them, never written to
the application log.
"""

from __future__ import annotations

import asyncio
import sys

from app.auth.allowlist import revoke_access
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.session import dispose_engine, get_session, init_engine


async def main(argv: list[str]) -> int:
    if not argv:
        print("Usage: make revoke-access EMAILS=a@example.com,b@example.com")
        return 1

    emails = [part.strip() for part in ",".join(argv).split(",") if part.strip()]
    if not emails:
        print("No addresses given.")
        return 1

    settings = get_settings()
    configure_logging(settings.log_level, is_local=settings.is_local)

    init_engine(settings)
    try:
        agen = get_session()
        db = await anext(agen)
        try:
            for email in emails:
                result = await revoke_access(db, email)
                sessions = (
                    f", {result.sessions_revoked} session(s) ended"
                    if result.sessions_revoked
                    else ""
                )
                print(f"  - {email}: {result.outcome}{sessions}")
        finally:
            await agen.aclose()
    finally:
        await dispose_engine()

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main(sys.argv[1:])))
