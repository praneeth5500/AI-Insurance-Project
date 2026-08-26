"""Policy upload (docs/11_BUILD_PLAN.md Phase 10).

The uploaded file is the first thing in this product that genuinely belongs
to the user, so most of these tests are about what must *not* happen to it:
it must not be accepted without being checked, must not be reachable by
anyone else, must not be written anywhere public, and must be genuinely
removable.
"""

from __future__ import annotations

import hashlib
import zlib
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.jobs.models import (
    JOB_FAILED,
    JOB_PROCESS_POLICY,
    JOB_QUEUED,
    JOB_RUNNING,
    ProcessingJob,
)
from app.jobs.queue import DatabaseJobQueue
from app.policies import service
from app.policies.errors import (
    DocumentNotFoundError,
    PolicyNotFoundError,
    TooManyDocumentsError,
    UploadRejectedError,
)
from app.policies.models import (
    STATUS_FAILED,
    STATUS_READING,
    PolicyDeletionAudit,
    PolicyDocument,
    UploadedPolicy,
)
from app.policies.schemas import PolicyView
from app.policies.storage import LocalFileStorage, StorageError, storage_key
from app.policies.validation import UploadRejected, validate_upload
from tests.test_questionnaire import make_user

# --------------------------------------------------------------- fixtures ---


REAL_PAGE_TEXT = (
    "This policy covers hospitalisation expenses subject to the terms, conditions and "
    "exclusions set out in the policy wording. Room rent is limited as stated in the "
    "schedule. Pre-existing diseases are covered after the waiting period stated below."
)


def pdf_bytes(*, pages: int = 1, text: str = REAL_PAGE_TEXT) -> bytes:
    """A real, minimal PDF.

    Built by hand rather than with a library so the fixture is exactly what it
    claims to be: these bytes are what a parser will actually see.

    Each line of `text` becomes its own text-showing operator at its own
    vertical position, because that is how a real PDF is laid out and it is
    what makes an extractor emit line breaks. A fixture that put a whole page
    on one line would quietly stop clause segmentation from ever being
    exercised.
    """
    objects: list[bytes] = []
    kids = " ".join(f"{4 + index * 2} 0 R" for index in range(pages))
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objects.append(f"<< /Type /Pages /Kids [{kids}] /Count {pages} >>".encode())
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    lines = text.split("\n") or [""]
    for index in range(pages):
        drawn = "\n".join(
            f"BT /F1 11 Tf 72 {740 - position * 16} Td ({_escape_pdf(line)}) Tj ET"
            for position, line in enumerate(lines)
            if line.strip()
        )
        stream = drawn.encode("latin-1", "replace")
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 3 0 R >> >> "
            f"/MediaBox [0 0 612 792] /Contents {5 + index * 2} 0 R >>".encode()
        )
        objects.append(
            b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream"
        )

    out = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{number} 0 obj\n".encode() + body + b"\nendobj\n"

    xref_at = len(out)
    out += f"xref\n0 {len(objects) + 1}\n".encode()
    out += b"0000000000 65535 f \n"
    for offset in offsets[1:]:
        out += f"{offset:010d} 00000 n \n".encode()
    out += (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_at}\n%%EOF"
    ).encode()
    return bytes(out)


def _escape_pdf(text: str) -> str:
    """Escape the three characters a PDF string literal cannot carry raw."""
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def scanned_pdf_bytes() -> bytes:
    """A PDF with no extractable text — what a scan looks like to a parser."""
    return pdf_bytes(text="")


PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n"
    + b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00"
    + zlib.crc32(b"IHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00").to_bytes(4, "big")
    + b"\x00\x00\x00\x00IEND\xaeB`\x82"
)

JPEG_BYTES = b"\xff\xd8\xff\xe0\x00\x10JFIF" + b"\x00" * 32 + b"\xff\xd9"


@pytest.fixture
def storage(tmp_path: Path) -> LocalFileStorage:
    return LocalFileStorage(Settings(app_env="local"), root=tmp_path / "uploads")


@pytest.fixture
def settings() -> Settings:
    return Settings(app_env="local", feature_policy_decoder=True)


async def upload(
    db: AsyncSession,
    user: object,
    storage: LocalFileStorage,
    settings: Settings,
    *,
    data: bytes | None = None,
    filename: str = "policy.pdf",
) -> service.PolicyWithDocuments:
    return await service.create_policy_from_upload(
        db,
        user=user,  # type: ignore[arg-type]
        storage=storage,
        queue=DatabaseJobQueue(db),
        settings=settings,
        filename=filename,
        data=data if data is not None else pdf_bytes(),
    )


# ------------------------------------------------------------- validation ---


def test_a_real_pdf_is_accepted() -> None:
    result = validate_upload(pdf_bytes(pages=3), max_bytes=1_000_000)

    assert result.mime_type == "application/pdf"
    assert result.page_count == 3
    assert result.has_text_layer is True


def test_a_scan_is_accepted_and_marked_as_needing_ocr() -> None:
    """docs/01_PRODUCT_SPEC.md section 3.2 supports scanned PDFs.

    A scan is not a failure — it is a document that needs a different reading
    path, and the worker has to be told which.
    """
    result = validate_upload(scanned_pdf_bytes(), max_bytes=1_000_000)

    assert result.mime_type == "application/pdf"
    assert result.has_text_layer is False


@pytest.mark.parametrize("data", [PNG_BYTES, JPEG_BYTES])
def test_photos_of_a_policy_are_accepted(data: bytes) -> None:
    result = validate_upload(data, max_bytes=1_000_000)

    assert result.mime_type in ("image/png", "image/jpeg")
    assert result.has_text_layer is False


def test_the_file_type_is_read_from_the_bytes_not_from_the_client() -> None:
    """A Content-Type header and a filename are both attacker-controlled.

    An executable renamed to .pdf must not become a stored "PDF".
    """
    with pytest.raises(UploadRejected) as raised:
        validate_upload(b"MZ\x90\x00" + b"\x00" * 200, max_bytes=1_000_000)

    assert raised.value.reason == "UNSUPPORTED_TYPE"


def test_an_empty_file_is_refused() -> None:
    with pytest.raises(UploadRejected) as raised:
        validate_upload(b"", max_bytes=1_000_000)

    assert raised.value.reason == "EMPTY_FILE"


def test_the_size_limit_is_enforced() -> None:
    with pytest.raises(UploadRejected) as raised:
        validate_upload(pdf_bytes(), max_bytes=10)

    assert raised.value.reason == "TOO_LARGE"


def test_a_corrupt_pdf_fails_with_something_the_reader_can_act_on() -> None:
    with pytest.raises(UploadRejected) as raised:
        validate_upload(b"%PDF-1.4\nthis is not a pdf", max_bytes=1_000_000)

    assert raised.value.reason == "CORRUPT_PDF"
    assert "downloading it from your insurer" in raised.value.message


def test_every_rejection_tells_the_reader_what_to_do_next() -> None:
    """A generic "upload failed" is useless to someone with a locked PDF."""
    from app.policies.validation import REJECTION_MESSAGES

    for reason, message in REJECTION_MESSAGES.items():
        assert message.endswith(".")
        assert len(message) > 40, reason
        # No internal vocabulary leaks into the reader's message.
        assert "MIME" not in message
        assert "exception" not in message.lower()


# ---------------------------------------------------------------- storage ---


def test_a_storage_key_is_built_from_identifiers_not_from_a_filename() -> None:
    """A filename can contain anything, including path traversal."""
    key = storage_key(user_id="usr_1", policy_id="pol_1", document_id="doc_1", extension="pdf")

    assert key == "policies/usr_1/pol_1/doc_1.pdf"


def test_storage_refuses_an_extension_that_is_not_alphanumeric() -> None:
    with pytest.raises(StorageError):
        storage_key(user_id="u", policy_id="p", document_id="d", extension="../../etc/passwd")


async def test_local_storage_writes_owner_only_files(
    storage: LocalFileStorage, tmp_path: Path
) -> None:
    await storage.put(key="policies/u/p/d.pdf", data=b"private")

    written = tmp_path / "uploads" / "policies" / "u" / "p" / "d.pdf"
    assert written.read_bytes() == b"private"
    assert oct(written.stat().st_mode)[-3:] == "600"


def test_local_storage_refuses_to_run_outside_local() -> None:
    """A container disk is not object storage, and losing beta users'
    documents on restart is worse than refusing to start."""
    with pytest.raises(RuntimeError, match="APP_ENV=local"):
        LocalFileStorage(
            Settings(app_env="production-beta", database_url="postgresql+asyncpg://x/y")
        )


async def test_storage_delete_is_idempotent(storage: LocalFileStorage) -> None:
    await storage.put(key="policies/u/p/d.pdf", data=b"x")
    await storage.delete(key="policies/u/p/d.pdf")
    await storage.delete(key="policies/u/p/d.pdf")

    assert await storage.exists(key="policies/u/p/d.pdf") is False


# ------------------------------------------------------------------ upload ---


async def test_an_upload_creates_a_policy_a_document_and_a_job(
    db: AsyncSession, storage: LocalFileStorage, settings: Settings
) -> None:
    user = await make_user(db)
    data = pdf_bytes(pages=2)

    result = await upload(db, user, storage, settings, data=data)

    assert result.policy.status == STATUS_READING
    assert len(result.documents) == 1
    document = result.documents[0]
    assert document.page_count == 2
    assert document.sha256 == hashlib.sha256(data).hexdigest()
    assert await storage.exists(key=document.storage_key)

    job = (await db.execute(select(ProcessingJob))).scalar_one()
    assert job.job_type == JOB_PROCESS_POLICY
    assert job.status == JOB_QUEUED


async def test_the_queued_job_carries_identifiers_and_nothing_else(
    db: AsyncSession, storage: LocalFileStorage, settings: Settings
) -> None:
    """docs/09_AWS_DEPLOYMENT.md section 8: identifiers, not raw content.

    A queue row that carried the document would be a second copy nobody is
    guarding.
    """
    user = await make_user(db)
    result = await upload(db, user, storage, settings)

    job = (await db.execute(select(ProcessingJob))).scalar_one()

    assert set(job.payload_json) == {"policyId", "documentId"}
    assert job.payload_json["policyId"] == result.policy.id
    serialised = str(job.payload_json)
    assert "%PDF" not in serialised
    assert "Policy wording" not in serialised


async def test_a_rejected_file_is_not_stored_and_leaves_no_record(
    db: AsyncSession, storage: LocalFileStorage, settings: Settings, tmp_path: Path
) -> None:
    """Validation happens before anything is written, so a refusal is clean."""
    user = await make_user(db)

    with pytest.raises(UploadRejectedError):
        await upload(db, user, storage, settings, data=b"not a document at all")

    assert (await db.execute(select(UploadedPolicy))).scalars().all() == []
    assert (await db.execute(select(PolicyDocument))).scalars().all() == []
    assert (await db.execute(select(ProcessingJob))).scalars().all() == []
    assert list((tmp_path / "uploads").rglob("*.pdf")) == []


async def test_the_display_name_comes_from_the_filename_without_trusting_it(
    db: AsyncSession, storage: LocalFileStorage, settings: Settings
) -> None:
    user = await make_user(db)

    result = await upload(
        db, user, storage, settings, filename="../../etc/My Health Policy 2026.pdf"
    )

    assert result.policy.display_name == "My Health Policy 2026"
    # And the key is unaffected by any of it.
    assert result.documents[0].storage_key.endswith(f"{result.documents[0].id}.pdf")


async def test_a_second_document_can_be_attached(
    db: AsyncSession, storage: LocalFileStorage, settings: Settings
) -> None:
    user = await make_user(db)
    first = await upload(db, user, storage, settings)

    result = await service.add_document(
        db,
        user=user,
        policy_id=first.policy.id,
        storage=storage,
        queue=DatabaseJobQueue(db),
        settings=settings,
        filename="schedule.pdf",
        data=pdf_bytes(text="Schedule"),
    )

    assert len(result.documents) == 2
    assert (await db.execute(select(ProcessingJob))).scalars().all().__len__() == 2


async def test_the_document_limit_is_enforced(db: AsyncSession, storage: LocalFileStorage) -> None:
    limited = Settings(app_env="local", feature_policy_decoder=True, max_documents_per_policy=1)
    user = await make_user(db)
    first = await upload(db, user, storage, limited)

    with pytest.raises(TooManyDocumentsError):
        await service.add_document(
            db,
            user=user,
            policy_id=first.policy.id,
            storage=storage,
            queue=DatabaseJobQueue(db),
            settings=limited,
            filename="another.pdf",
            data=pdf_bytes(),
        )


# ----------------------------------------------------------- authorization ---


async def test_one_user_cannot_read_another_users_policy(
    db: AsyncSession, storage: LocalFileStorage, settings: Settings
) -> None:
    owner = await make_user(db, "owner@example.com")
    intruder = await make_user(db, "intruder@example.com")
    result = await upload(db, owner, storage, settings)

    with pytest.raises(PolicyNotFoundError):
        await service.get_policy(db, user=intruder, policy_id=result.policy.id)


async def test_one_user_cannot_download_another_users_document(
    db: AsyncSession, storage: LocalFileStorage, settings: Settings
) -> None:
    """docs/12_BETA_CHECKLIST.md: cross-user access test passes."""
    owner = await make_user(db, "owner@example.com")
    intruder = await make_user(db, "intruder@example.com")
    result = await upload(db, owner, storage, settings)

    with pytest.raises(PolicyNotFoundError):
        await service.read_document(
            db,
            user=intruder,
            policy_id=result.policy.id,
            document_id=result.documents[0].id,
            storage=storage,
        )


async def test_one_user_cannot_delete_another_users_policy(
    db: AsyncSession, storage: LocalFileStorage, settings: Settings
) -> None:
    owner = await make_user(db, "owner@example.com")
    intruder = await make_user(db, "intruder@example.com")
    result = await upload(db, owner, storage, settings)

    with pytest.raises(PolicyNotFoundError):
        await service.delete_policy(db, user=intruder, policy_id=result.policy.id, storage=storage)

    assert await storage.exists(key=result.documents[0].storage_key)


async def test_a_document_id_from_another_policy_is_refused(
    db: AsyncSession, storage: LocalFileStorage, settings: Settings
) -> None:
    user = await make_user(db)
    first = await upload(db, user, storage, settings)
    second = await upload(db, user, storage, settings, filename="other.pdf")

    with pytest.raises(DocumentNotFoundError):
        await service.read_document(
            db,
            user=user,
            policy_id=first.policy.id,
            document_id=second.documents[0].id,
            storage=storage,
        )


# --------------------------------------------------------------- deletion ---


async def test_deleting_a_policy_removes_the_bytes(
    db: AsyncSession, storage: LocalFileStorage, settings: Settings
) -> None:
    user = await make_user(db)
    result = await upload(db, user, storage, settings)
    key = result.documents[0].storage_key

    await service.delete_policy(db, user=user, policy_id=result.policy.id, storage=storage)

    assert await storage.exists(key=key) is False
    with pytest.raises(PolicyNotFoundError):
        await service.get_policy(db, user=user, policy_id=result.policy.id)


async def test_a_deletion_is_auditable_without_recording_the_document(
    db: AsyncSession, storage: LocalFileStorage, settings: Settings
) -> None:
    user = await make_user(db)
    result = await upload(db, user, storage, settings, filename="Sensitive Policy.pdf")

    await service.delete_policy(db, user=user, policy_id=result.policy.id, storage=storage)

    audit = (await db.execute(select(PolicyDeletionAudit))).scalar_one()
    assert audit.documents_removed == 1
    assert audit.storage_confirmed is True
    # The audit proves the deletion; it must not preserve what was deleted.
    assert "Sensitive" not in str(audit.detail)


async def test_a_deletion_that_cannot_confirm_storage_says_so(
    db: AsyncSession, storage: LocalFileStorage, settings: Settings
) -> None:
    """Reporting a clean deletion we cannot vouch for is worse than admitting
    a problem: someone has to know the bytes may still be out there."""
    user = await make_user(db)
    result = await upload(db, user, storage, settings)

    async def refuse(*, key: str) -> None:
        raise StorageError("storage unavailable")

    storage.delete = refuse  # type: ignore[method-assign]

    await service.delete_policy(db, user=user, policy_id=result.policy.id, storage=storage)

    audit = (await db.execute(select(PolicyDeletionAudit))).scalar_one()
    assert audit.storage_confirmed is False
    assert audit.documents_removed == 0
    assert audit.detail is not None and "could not be confirmed" in audit.detail


# ------------------------------------------------------------------ queue ---


async def test_a_job_is_claimed_once(db: AsyncSession) -> None:
    queue = DatabaseJobQueue(db)
    await queue.enqueue(job_type=JOB_PROCESS_POLICY, payload={"policyId": "pol_1"})
    await db.flush()

    first = await queue.claim(worker_id="worker-a")
    second = await queue.claim(worker_id="worker-a")

    assert first is not None
    assert second is None


async def test_a_failed_job_is_retried_until_its_attempts_run_out(db: AsyncSession) -> None:
    queue = DatabaseJobQueue(db)
    job_id = await queue.enqueue(job_type=JOB_PROCESS_POLICY, payload={"policyId": "pol_1"})
    await db.flush()

    job = (await db.execute(select(ProcessingJob).where(ProcessingJob.id == job_id))).scalar_one()
    job.max_attempts = 2
    await db.flush()

    await queue.claim(worker_id="w")
    await queue.fail(job_id=job_id, error="temporary")
    await db.flush()
    await db.refresh(job)
    assert job.status == JOB_QUEUED

    job.available_at = job.created_at
    await queue.claim(worker_id="w")
    await queue.fail(job_id=job_id, error="temporary")
    await db.flush()
    await db.refresh(job)
    assert job.status == JOB_FAILED


async def test_a_failure_that_will_not_succeed_on_retry_fails_immediately(
    db: AsyncSession,
) -> None:
    """A password-protected PDF will still be password-protected next time."""
    queue = DatabaseJobQueue(db)
    job_id = await queue.enqueue(job_type=JOB_PROCESS_POLICY, payload={"policyId": "pol_1"})
    await db.flush()
    await queue.claim(worker_id="w")

    await queue.fail(job_id=job_id, error="ENCRYPTED_PDF", retry=False)
    await db.flush()

    job = (await db.execute(select(ProcessingJob).where(ProcessingJob.id == job_id))).scalar_one()
    assert job.status == JOB_FAILED


async def test_an_error_message_is_bounded(db: AsyncSession) -> None:
    """An unbounded error field is a place document content could end up."""
    queue = DatabaseJobQueue(db)
    job_id = await queue.enqueue(job_type=JOB_PROCESS_POLICY, payload={"policyId": "pol_1"})
    await db.flush()
    await queue.claim(worker_id="w")

    await queue.fail(job_id=job_id, error="x" * 10_000, retry=False)
    await db.flush()

    job = (await db.execute(select(ProcessingJob).where(ProcessingJob.id == job_id))).scalar_one()
    assert job.last_error is not None
    assert len(job.last_error) <= 2000


async def test_a_claim_marks_the_job_running(db: AsyncSession) -> None:
    queue = DatabaseJobQueue(db)
    await queue.enqueue(job_type=JOB_PROCESS_POLICY, payload={"policyId": "pol_1"})
    await db.flush()

    claimed = await queue.claim(worker_id="worker-a")
    await db.flush()

    assert claimed is not None
    job = (await db.execute(select(ProcessingJob))).scalar_one()
    assert job.status == JOB_RUNNING
    assert job.claimed_by == "worker-a"
    assert job.attempts == 1


# --------------------------------------------------------- processing view ---


async def test_the_stage_list_shows_where_processing_has_reached(
    db: AsyncSession, storage: LocalFileStorage, settings: Settings
) -> None:
    """docs/02_UX_UI_SPEC.md section 14: stages, no fake percentages."""
    user = await make_user(db)
    result = await upload(db, user, storage, settings)

    view = PolicyView.of(result)
    states = {stage.key: stage.state for stage in view.stages}

    assert states["RECEIVED"] == "DONE"
    assert states["READING"] == "CURRENT"
    assert states["READY"] == "PENDING"
    # Nothing anywhere in the payload is a percentage.
    assert "percent" not in view.model_dump_json().lower()


async def test_a_failed_policy_says_what_the_reader_can_do(
    db: AsyncSession, storage: LocalFileStorage, settings: Settings
) -> None:
    """CLAUDE.md: a failed extraction must remain visibly failed."""
    user = await make_user(db)
    result = await upload(db, user, storage, settings)
    result.policy.status = STATUS_FAILED
    result.policy.failure_reason = "ENCRYPTED_PDF"

    view = PolicyView.of(result)

    assert view.is_failed is True
    assert view.is_ready is False
    assert view.failure_message is not None
    assert "password-protected" in view.failure_message


# ------------------------------------------------------------ feature flag ---


async def test_the_upload_endpoints_are_absent_while_the_feature_is_off(
    api: AsyncClient,
) -> None:
    """The flag is enforced on the server, not just hidden in the UI.

    An endpoint that quietly accepted policy documents while the product said
    the feature did not exist would be collecting private files it has nothing
    to do with.
    """
    response = await api.get("/api/v1/policies")

    assert response.status_code in (401, 404)
