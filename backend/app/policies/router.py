"""Policy upload endpoints (docs/08_API_CONTRACTS.md section 7).

The contract describes returning "presigned/private upload instructions or
upload session". Presigning needs an object store, and one is not chosen yet,
so this implements the other half of that sentence: the file is posted to the
API, which validates it before anything is written. Recorded in
`docs/SPEC_ISSUES.md` — the storage interface is shaped so a presigned flow
can be added without changing callers.

Every route requires a signed-in user *and* the decoder feature flag. A
document is only ever returned through `GET .../documents/{id}`, which
re-checks ownership on each request — there is no public URL anywhere.
"""

from __future__ import annotations

from fastapi import APIRouter, File, Form, UploadFile, status
from fastapi.responses import Response

from app.auth.dependencies import AppSettings, CurrentUser, DbSession
from app.core.errors import RateLimitedError
from app.core.rate_limit import UPLOAD_PER_USER, limiter
from app.policies import service
from app.policies.dependencies import DecoderEnabled, Queue, Storage
from app.policies.models import PolicyDocument
from app.policies.schemas import (
    DeleteResponse,
    PolicyListView,
    PolicySummaryView,
    PolicyView,
)

router = APIRouter(prefix="/policies", tags=["policies"], dependencies=[DecoderEnabled])

#: Extension per accepted type, for the download filename.
_DOWNLOAD_EXTENSIONS = {"application/pdf": "pdf", "image/png": "png", "image/jpeg": "jpg"}


def _download_name(document: PolicyDocument) -> str:
    return f"policy-document.{_DOWNLOAD_EXTENSIONS.get(document.mime_type, 'bin')}"


@router.post(
    "/uploads",
    response_model=PolicyView,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a policy document",
)
async def upload_policy(
    user: CurrentUser,
    db: DbSession,
    storage: Storage,
    queue: Queue,
    settings: AppSettings,
    file: UploadFile = File(...),  # noqa: B008 - FastAPI's own idiom
    domain: str | None = Form(default=None),  # noqa: B008 - FastAPI's own idiom
) -> PolicyView:
    """Accept one file and start processing it.

    The whole body is read into memory deliberately: the type has to be
    determined from the bytes before anything is written, and the size limit
    is small enough that streaming to a temporary file would add a second
    place a private document can be left behind.
    """
    # Each upload parses a PDF, so the limit is per user rather than per IP:
    # a signed-in account is the thing doing the work.
    if not limiter.check(f"upload:{user.id}", UPLOAD_PER_USER):
        raise RateLimitedError

    data = await file.read()
    result = await service.create_policy_from_upload(
        db,
        user=user,
        storage=storage,
        queue=queue,
        settings=settings,
        filename=file.filename or "policy",
        data=data,
        domain=domain,
    )
    return PolicyView.of(result)


@router.get("", response_model=PolicyListView, summary="Your uploaded policies")
async def list_policies(user: CurrentUser, db: DbSession) -> PolicyListView:
    policies = await service.list_policies(db, user=user)
    return PolicyListView(policies=[PolicySummaryView.of(policy) for policy in policies])


@router.get("/{policy_id}", response_model=PolicyView, summary="One uploaded policy")
async def get_policy(policy_id: str, user: CurrentUser, db: DbSession) -> PolicyView:
    return PolicyView.of(await service.get_policy(db, user=user, policy_id=policy_id))


@router.post(
    "/{policy_id}/documents",
    response_model=PolicyView,
    status_code=status.HTTP_201_CREATED,
    summary="Attach another document",
)
async def add_document(
    policy_id: str,
    user: CurrentUser,
    db: DbSession,
    storage: Storage,
    queue: Queue,
    settings: AppSettings,
    file: UploadFile = File(...),  # noqa: B008 - FastAPI's own idiom
) -> PolicyView:
    if not limiter.check(f"upload:{user.id}", UPLOAD_PER_USER):
        raise RateLimitedError

    result = await service.add_document(
        db,
        user=user,
        policy_id=policy_id,
        storage=storage,
        queue=queue,
        settings=settings,
        filename=file.filename or "document",
        data=await file.read(),
    )
    return PolicyView.of(result)


@router.get(
    "/{policy_id}/documents/{document_id}",
    summary="Download one of your documents",
    response_class=Response,
)
async def download_document(
    policy_id: str, document_id: str, user: CurrentUser, db: DbSession, storage: Storage
) -> Response:
    """Stream a document back to the person who uploaded it.

    `Content-Disposition: attachment` and `X-Content-Type-Options: nosniff`
    together stop an uploaded file being rendered in the origin's context —
    an uploaded SVG or HTML masquerading as an image is a classic route to
    running script against the user's own session.
    """
    document, data = await service.read_document(
        db, user=user, policy_id=policy_id, document_id=document_id, storage=storage
    )
    return Response(
        content=data,
        media_type=document.mime_type,
        headers={
            # A generic name: the reader's own filename is untrusted text and
            # putting it in a header invites header injection.
            "Content-Disposition": f'attachment; filename="{_download_name(document)}"',
            # Stops an uploaded file being rendered in the origin's context.
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "private, no-store",
        },
    )


@router.delete("/{policy_id}", response_model=DeleteResponse, summary="Delete a policy")
async def delete_policy(
    policy_id: str, user: CurrentUser, db: DbSession, storage: Storage
) -> DeleteResponse:
    await service.delete_policy(db, user=user, policy_id=policy_id, storage=storage)
    return DeleteResponse(id=policy_id, deleted=True)
