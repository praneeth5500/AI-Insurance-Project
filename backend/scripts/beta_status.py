"""Who holds an invite, and who has actually used it.

    make beta-status

The address that was invited but has never signed in is the one worth looking
at: it usually means the sign-in mail is not arriving, which is invisible from
inside the application.

Prints to the operator's terminal only. Nothing here goes to the application
log — an invited address is personal data.
"""

from __future__ import annotations

import asyncio
import sys

from app.auth.allowlist import beta_roster
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.session import dispose_engine, get_session, init_engine


async def main() -> int:
    settings = get_settings()
    configure_logging(settings.log_level, is_local=settings.is_local)

    init_engine(settings)
    try:
        agen = get_session()
        db = await anext(agen)
        try:
            roster = await beta_roster(db)
        finally:
            await agen.aclose()
    finally:
        await dispose_engine()

    if not roster:
        print("Nobody has been invited yet.")
        print("Set BETA_ALLOWLIST_EMAILS in .env and run `make seed-allowlist`.")
        return 0

    print(f"{'ADDRESS':<40} {'STATUS':<10} {'SESSIONS':>8}  LAST SIGN-IN")
    for entry in roster:
        status = entry.status if entry.allowlisted else f"{entry.status}*"
        last = entry.last_login_at.strftime("%Y-%m-%d %H:%M") if entry.last_login_at else "never"
        print(f"{entry.email:<40} {status:<10} {entry.active_sessions:>8}  {last}")

    never = sum(1 for entry in roster if entry.last_login_at is None and entry.allowlisted)
    print()
    print(f"{len(roster)} invited · {never} have never signed in")
    if never:
        print("An invite that is never used usually means the mail is not arriving.")
    print("* = not on the allowlist")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
