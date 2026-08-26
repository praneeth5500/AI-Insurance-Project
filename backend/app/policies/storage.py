"""Where an uploaded policy actually lives.

`docs/09_AWS_DEPLOYMENT.md` section 5 sets the requirements: block public
access, encrypt at rest, separate by environment, signed temporary URLs, a
lifecycle policy and a deletion path. The bucket is not chosen yet
(`docs/13_DECISIONS_AND_OPEN_ITEMS.md` open item 4 covers the queue; the
storage vendor is equally undecided), so this is an interface with a local
implementation.

The rules that must hold whatever the implementation are enforced here rather
than left to the adapter:

* **Nothing is ever publicly readable.** `CLAUDE.md` rule 7. The local
  implementation writes outside the repository and outside anything the web
  server serves, and no code path returns a URL a browser could fetch
  directly — bytes are streamed back through an authenticated endpoint.
* **A storage key never contains user input.** Filenames arrive from the
  client and can contain anything at all, including path separators. The key
  is derived from identifiers we generated.
* **Deletion is part of the interface.** `docs/12_BETA_CHECKLIST.md` requires
  a working delete path, and an interface without one invites a service that
  cannot honour it.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from app.core.config import Settings


class StorageError(RuntimeError):
    """The file could not be stored or retrieved."""


class FileStorage(Protocol):
    """The storage seam. Implementations must never expose a public URL."""

    async def put(self, *, key: str, data: bytes) -> None: ...

    async def get(self, *, key: str) -> bytes: ...

    async def delete(self, *, key: str) -> None: ...

    async def exists(self, *, key: str) -> bool: ...


def storage_key(*, user_id: str, policy_id: str, document_id: str, extension: str) -> str:
    """Build a key from identifiers we generated, never from a filename.

    The user id is the first segment so that a future bucket policy can scope
    access per user with a prefix condition, and so an accidental listing
    cannot mix one person's documents with another's.
    """
    safe_extension = extension.lower().lstrip(".")
    if not safe_extension.isalnum():
        raise StorageError("Refusing to build a storage key from a non-alphanumeric extension.")
    return f"policies/{user_id}/{policy_id}/{document_id}.{safe_extension}"


class LocalFileStorage:
    """Development storage: a private directory on disk.

    Not a stand-in for S3's guarantees — it has no encryption at rest and no
    lifecycle policy — which is why it refuses to run outside `local`. A
    deployed environment must configure a real adapter rather than silently
    writing beta users' policy documents to a container filesystem that
    disappears on restart.
    """

    def __init__(self, settings: Settings, root: Path | None = None) -> None:
        if not settings.is_local:
            raise RuntimeError(
                "LocalFileStorage is for APP_ENV=local only; configure an encrypted "
                "object-storage adapter (docs/09_AWS_DEPLOYMENT.md section 5) before "
                "deploying. Uploaded policies must not be written to a container disk."
            )
        self._root = root or Path(settings.upload_storage_dir)

    def _path(self, key: str) -> Path:
        candidate = (self._root / key).resolve()
        root = self._root.resolve()
        # A key is generated internally, but resolving and re-checking costs
        # nothing and turns a future mistake into an error instead of a write
        # outside the storage root.
        if not candidate.is_relative_to(root):
            raise StorageError("Storage key escapes the storage root.")
        return candidate

    async def put(self, *, key: str, data: bytes) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        # Owner-only. The directory is already private; this makes the file
        # private too even if the directory is later relaxed.
        path.chmod(0o600)

    async def get(self, *, key: str) -> bytes:
        path = self._path(key)
        if not path.exists():
            raise StorageError("Stored document is missing.")
        return path.read_bytes()

    async def delete(self, *, key: str) -> None:
        path = self._path(key)
        # Deleting what is already gone is not an error: the point is that the
        # bytes are not there afterwards.
        path.unlink(missing_ok=True)

    async def exists(self, *, key: str) -> bool:
        return self._path(key).exists()


def build_file_storage(settings: Settings) -> FileStorage:
    """Select the adapter for this environment.

    Deployed environments fail closed, exactly as the email provider does:
    refusing to start is better than accepting a user's policy document and
    putting it somewhere that cannot keep it.
    """
    if settings.is_local:
        return LocalFileStorage(settings)
    raise RuntimeError(
        "No object-storage adapter is configured. Implement a FileStorage adapter "
        "(for example S3 with block-public-access and SSE enabled, per "
        "docs/09_AWS_DEPLOYMENT.md section 5) and select it here before deploying."
    )
