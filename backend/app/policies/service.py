"""Accepting a policy document and getting it queued for processing.

The flow, and the order it happens in, is the whole design:

    validate the bytes -> create the records -> store the bytes
      -> enqueue the job -> commit

Validation comes first so a file we will not process is never written
anywhere. The commit comes last so a queued job can never reference a policy
row that was rolled back. Storage sits between the two because it is the only
step that is not transactional — if it fails, the transaction is abandoned and
nothing is left pointing at bytes that are not there.

`docs/09_AWS_DEPLOYMENT.md` section 8: the queued message carries identifiers
only. The worker fetches the file itself through an authorised path, so a
queue row never becomes a second copy of someone's policy.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics import service as analytics
from app.analytics.events import POLICY_UPLOAD_COMPLETED
from app.core.config import Settings
from app.core.logging import log_fields
from app.db.types import utcnow
from app.jobs.models import JOB_PROCESS_POLICY
from app.jobs.queue import JobQueue
from app.policies.errors import (
    DocumentNotFoundError,
    PolicyNotFoundError,
    TooManyDocumentsError,
    UploadRejectedError,
)
from app.policies.models import (
    STATUS_READING,
    STATUS_RECEIVED,
    PolicyDeletionAudit,
    PolicyDocument,
    UploadedPolicy,
)
from app.policies.storage import FileStorage, StorageError, storage_key
from app.policies.validation import UploadRejected, validate_upload
from app.users.models import User

logger = logging.getLogger(__name__)

#: How long a display name may be before it is trimmed. The reader's filename
#: is used as the default and filenames can be arbitrarily long.
MAX_DISPLAY_NAME = 120


@dataclass(frozen=True)
class PolicyWithDocuments:
    policy: UploadedPolicy
    documents: list[PolicyDocument]


def _display_name(filename: str) -> str:
    """A readable default name from the reader's filename.

    Treated purely as display text. It is never used to build a storage key
    or a path, so a filename containing separators or traversal sequences is
    harmless here — but it is still trimmed and stripped of control
    characters so it cannot break the UI that shows it.
    """
    cleaned = "".join(character for character in filename if character.isprintable()).strip()
    stem = cleaned.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    if "." in stem:
        stem = stem.rsplit(".", 1)[0]
    stem = stem.strip() or "Your policy"
    return stem[:MAX_DISPLAY_NAME]


async def create_policy_from_upload(
    db: AsyncSession,
    *,
    user: User,
    storage: FileStorage,
    queue: JobQueue,
    settings: Settings,
    filename: str,
    data: bytes,
    domain: str | None = None,
) -> PolicyWithDocuments:
    """Accept one file and start processing it."""
    try:
        validated = validate_upload(data, max_bytes=settings.max_upload_bytes)
    except UploadRejected as rejection:
        # The reason travels to the client so the message can be specific;
        # the file itself is never written.
        raise UploadRejectedError(rejection.message) from rejection

    policy = UploadedPolicy(
        user_id=user.id,
        domain=domain,
        display_name=_display_name(filename),
        status=STATUS_RECEIVED,
    )
    db.add(policy)
    await db.flush()

    document = PolicyDocument(
        policy_id=policy.id,
        storage_key="",  # replaced below, once the ids exist
        filename=filename[:255],
        mime_type=validated.mime_type,
        size_bytes=validated.size_bytes,
        sha256=validated.sha256,
        page_count=validated.page_count,
        is_encrypted=False,
        metadata_json=validated.metadata,
    )
    db.add(document)
    await db.flush()

    document.storage_key = storage_key(
        user_id=user.id,
        policy_id=policy.id,
        document_id=document.id,
        extension=validated.extension,
    )

    try:
        await storage.put(key=document.storage_key, data=data)
    except StorageError:
        await db.rollback()
        raise

    await queue.enqueue(
        job_type=JOB_PROCESS_POLICY,
        # Identifiers only (docs/09_AWS_DEPLOYMENT.md section 8).
        payload={"policyId": policy.id, "documentId": document.id},
        policy_id=policy.id,
    )
    policy.status = STATUS_READING
    await analytics.record_safely(
        db,
        name=POLICY_UPLOAD_COMPLETED,
        user=user,
        # Never the filename, and never anything that identifies the document.
        properties={"page_count": validated.page_count},
    )
    await db.commit()

    logger.info(
        "policy_upload_completed",
        extra=log_fields(
            event="policy_upload_completed",
            user_id=user.id,
            resource_type="uploaded_policy",
            resource_id=policy.id,
        ),
    )
    return PolicyWithDocuments(policy=policy, documents=[document])


async def add_document(
    db: AsyncSession,
    *,
    user: User,
    policy_id: str,
    storage: FileStorage,
    queue: JobQueue,
    settings: Settings,
    filename: str,
    data: bytes,
) -> PolicyWithDocuments:
    """Attach another file to a policy — a schedule alongside the wording."""
    existing = await get_policy(db, user=user, policy_id=policy_id)
    if len(existing.documents) >= settings.max_documents_per_policy:
        raise TooManyDocumentsError

    try:
        validated = validate_upload(data, max_bytes=settings.max_upload_bytes)
    except UploadRejected as rejection:
        raise UploadRejectedError(rejection.message) from rejection

    document = PolicyDocument(
        policy_id=existing.policy.id,
        storage_key="",
        filename=filename[:255],
        mime_type=validated.mime_type,
        size_bytes=validated.size_bytes,
        sha256=validated.sha256,
        page_count=validated.page_count,
        metadata_json=validated.metadata,
    )
    db.add(document)
    await db.flush()
    document.storage_key = storage_key(
        user_id=user.id,
        policy_id=existing.policy.id,
        document_id=document.id,
        extension=validated.extension,
    )

    try:
        await storage.put(key=document.storage_key, data=data)
    except StorageError:
        await db.rollback()
        raise

    await queue.enqueue(
        job_type=JOB_PROCESS_POLICY,
        payload={"policyId": existing.policy.id, "documentId": document.id},
        policy_id=existing.policy.id,
    )
    existing.policy.status = STATUS_READING
    await db.commit()

    return await get_policy(db, user=user, policy_id=policy_id)


async def get_policy(db: AsyncSession, *, user: User, policy_id: str) -> PolicyWithDocuments:
    """One policy, scoped to its owner.

    Ownership is part of the query rather than a check afterwards, so there is
    no version of this function that can return someone else's policy.
    """
    policy = (
        await db.execute(
            select(UploadedPolicy).where(
                UploadedPolicy.id == policy_id,
                UploadedPolicy.user_id == user.id,
                UploadedPolicy.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if policy is None:
        raise PolicyNotFoundError

    documents = list(
        (
            await db.execute(
                select(PolicyDocument)
                .where(
                    PolicyDocument.policy_id == policy.id,
                    PolicyDocument.deleted_at.is_(None),
                )
                .order_by(PolicyDocument.created_at)
            )
        )
        .scalars()
        .all()
    )
    return PolicyWithDocuments(policy=policy, documents=documents)


async def list_policies(db: AsyncSession, *, user: User) -> list[UploadedPolicy]:
    return list(
        (
            await db.execute(
                select(UploadedPolicy)
                .where(
                    UploadedPolicy.user_id == user.id,
                    UploadedPolicy.deleted_at.is_(None),
                )
                .order_by(UploadedPolicy.created_at.desc())
            )
        )
        .scalars()
        .all()
    )


async def read_document(
    db: AsyncSession, *, user: User, policy_id: str, document_id: str, storage: FileStorage
) -> tuple[PolicyDocument, bytes]:
    """The bytes of one document, for its owner only.

    This is the only way a document leaves storage. There is deliberately no
    public URL and no signed link handed to the browser: the file is streamed
    through an authenticated endpoint, so access is re-checked on every read
    and cannot outlive the reader's session (`CLAUDE.md` rule 7).
    """
    policy = await get_policy(db, user=user, policy_id=policy_id)
    document = next((item for item in policy.documents if item.id == document_id), None)
    if document is None:
        raise DocumentNotFoundError

    try:
        return document, await storage.get(key=document.storage_key)
    except StorageError as exc:
        raise DocumentNotFoundError from exc


async def delete_policy(
    db: AsyncSession, *, user: User, policy_id: str, storage: FileStorage
) -> None:
    """Remove a policy and every document belonging to it.

    The bytes go first. If storage fails, the audit records that the objects
    may still exist rather than claiming a clean deletion — a delete path that
    reports success it cannot vouch for is worse than one that admits a
    problem (`docs/12_BETA_CHECKLIST.md`).
    """
    existing = await get_policy(db, user=user, policy_id=policy_id)
    now = utcnow()

    failures: list[str] = []
    for document in existing.documents:
        try:
            await storage.delete(key=document.storage_key)
        except StorageError:
            failures.append(document.id)
        document.deleted_at = now

    existing.policy.deleted_at = now

    db.add(
        PolicyDeletionAudit(
            user_id=user.id,
            policy_id=existing.policy.id,
            documents_removed=len(existing.documents) - len(failures),
            storage_confirmed=not failures,
            detail=(
                None
                if not failures
                else f"{len(failures)} object(s) could not be confirmed removed from storage."
            ),
        )
    )
    await db.commit()

    logger.info(
        "policy_deleted",
        extra=log_fields(
            event="policy_deleted",
            user_id=user.id,
            resource_type="uploaded_policy",
            resource_id=policy_id,
        ),
    )
