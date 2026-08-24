"""Token generation and comparison for authentication.

Magic-link and session tokens are **opaque random values**, stored only as a
SHA-256 digest. docs/04_BACKEND_ARCHITECTURE.md section 7 asks for a
"signed/expiring token" with "one-time use where practical" and "session
revocation"; a random token checked against a database row satisfies all three
and, unlike a self-contained signed token, can genuinely be revoked before it
expires. It also means there is no signing secret to leak.

A leaked database still cannot be replayed against the API, because only the
digest is stored.
"""

from __future__ import annotations

import hashlib
import secrets

#: 32 bytes of entropy, URL-safe. Long enough that guessing is not a threat.
TOKEN_BYTES = 32


def generate_token() -> str:
    """Return a fresh, URL-safe secret. Shown to the user exactly once."""
    return secrets.token_urlsafe(TOKEN_BYTES)


def hash_token(token: str) -> str:
    """Return the digest stored in the database. Never store the token itself."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def tokens_match(candidate: str, stored_hash: str) -> bool:
    """Compare in constant time, so timing cannot reveal a valid prefix."""
    return secrets.compare_digest(hash_token(candidate), stored_hash)


def normalize_email(email: str) -> str:
    """Emails are matched case-insensitively and stored lowercase."""
    return email.strip().lower()
