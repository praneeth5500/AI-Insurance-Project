"""Running a policy through extraction.

`docs/07_POLICY_DECODER_AI.md` section 2, from private storage onwards:

    native PDF extraction -> OCR fallback -> page normalisation
      -> clause segmentation -> structured extraction -> validation
      -> policy facts

The stage the policy reports moves as the pipeline advances, so the reader's
screen reflects real progress rather than a timer. `docs/02_UX_UI_SPEC.md`
section 14 rules out fake percentages, and a stage that advances before the
work is done is the same lie in a different shape.

Failure is a first-class outcome. `CLAUDE.md`: a failed extraction must remain
visibly failed. A run that cannot read a scan records `SCAN_NEEDS_OCR` and the
policy shows a message saying so — it does not quietly produce an empty
policy, which a reader would reasonably read as "my policy covers nothing".
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics import service as analytics
from app.analytics.events import POLICY_PROCESSING_COMPLETED
from app.core.logging import log_fields
from app.db.types import utcnow
from app.extraction.clauses import segment
from app.extraction.facts import FactExtractor, build_fact_extractor
from app.extraction.models import (
    RUN_FAILED,
    RUN_RUNNING,
    RUN_SUCCEEDED,
    ExtractionRun,
    PolicyClause,
    PolicyFact,
    PolicyPage,
)
from app.extraction.ocr import OcrProvider, build_ocr_provider
from app.extraction.text import ExtractionFailed, extract_pages
from app.policies.models import (
    STATUS_BUILDING_SUMMARY,
    STATUS_FAILED,
    STATUS_FINDING_CLAUSES,
    STATUS_PREPARING_QA,
    STATUS_READING,
    STATUS_READY,
    PolicyDocument,
    UploadedPolicy,
)
from app.policies.storage import FileStorage, StorageError

logger = logging.getLogger(__name__)

#: Reader-facing wording for each failure. Written from a known set of causes
#: so a message can be specific without ever echoing document content.
FAILURE_MESSAGES: dict[str, str] = {
    "SCAN_NEEDS_OCR": (
        "That document is a scan or a photo, and reading scans isn't part of this beta yet. "
        "If your insurer offers a text PDF of the same policy, that will work."
    ),
    "ENCRYPTED_PDF": (
        "That PDF is password-protected, so we can't open it. Please save an unlocked copy "
        "and upload that instead."
    ),
    "CORRUPT_PDF": (
        "We couldn't open that PDF. It may not have downloaded fully — please download it "
        "from your insurer again and re-upload."
    ),
    "NO_PAGES": (
        "That document has no pages we can read. Please check the file opened correctly "
        "before you uploaded it, and try again."
    ),
    "NO_TEXT": (
        "We opened the document but couldn't find any readable text in it. If it is a scan, "
        "reading scans isn't part of this beta yet."
    ),
    "DOCUMENT_MISSING": ("We couldn't retrieve the file you uploaded. Please upload it again."),
}


@dataclass(frozen=True)
class ExtractionResult:
    run_id: str
    pages: int
    clauses: int
    facts_found: int
    facts_not_found: int


async def process_document(
    db: AsyncSession,
    *,
    policy_id: str,
    document_id: str,
    storage: FileStorage,
    ocr: OcrProvider | None = None,
    extractor: FactExtractor | None = None,
) -> ExtractionResult:
    """Read one document and store what it says.

    Raises `ExtractionFailed` after recording the failure, so the caller can
    decide whether the job is worth retrying — a password-protected PDF will
    still be password-protected next time, and retrying it three times only
    delays telling the reader.
    """
    ocr = ocr or build_ocr_provider()
    extractor = extractor or build_fact_extractor()

    policy = (
        await db.execute(select(UploadedPolicy).where(UploadedPolicy.id == policy_id))
    ).scalar_one_or_none()
    document = (
        await db.execute(select(PolicyDocument).where(PolicyDocument.id == document_id))
    ).scalar_one_or_none()
    if policy is None or document is None:
        raise ExtractionFailed("DOCUMENT_MISSING")

    run = ExtractionRun(
        policy_id=policy.id,
        schema_version=extractor.schema_version,
        # Null until OCR actually runs: recording a provider that did nothing
        # would misdescribe the run.
        ocr_provider=None,
        # No model participates in this pipeline. Recorded as null rather than
        # left ambiguous, so a run can always answer "did an AI touch this?".
        ai_provider=None,
        model=None,
        prompt_version=None,
        status=RUN_RUNNING,
    )
    db.add(run)
    await db.flush()

    async def fail(reason: str) -> None:
        run.status = RUN_FAILED
        run.failure_reason = reason
        run.completed_at = utcnow()
        policy.status = STATUS_FAILED
        policy.failure_reason = reason
        # A failure is a funnel step too: how often extraction cannot read a
        # document is the number that decides whether OCR is worth buying.
        await analytics.record_safely(
            db, name=POLICY_PROCESSING_COMPLETED, properties={"outcome": reason}
        )
        await db.commit()
        logger.info(
            "policy_processing_failed",
            extra=log_fields(
                event="policy_processing_failed",
                resource_type="uploaded_policy",
                resource_id=policy.id,
            ),
        )

    # ---------------------------------------------------------- reading ----
    policy.status = STATUS_READING
    await db.flush()

    try:
        data = await storage.get(key=document.storage_key)
    except StorageError as exc:
        await fail("DOCUMENT_MISSING")
        raise ExtractionFailed("DOCUMENT_MISSING") from exc

    try:
        pages, ocr_used = await extract_pages(data, mime_type=document.mime_type, ocr=ocr)
    except ExtractionFailed as failure:
        await fail(failure.reason)
        raise

    if not any(page.text for page in pages):
        await fail("NO_TEXT")
        raise ExtractionFailed("NO_TEXT")

    run.ocr_provider = ocr_used
    for page in pages:
        db.add(
            PolicyPage(
                document_id=document.id,
                page_number=page.page_number,
                text=page.text,
                extraction_method=page.method,
                confidence=page.confidence,
            )
        )
    await db.flush()

    # -------------------------------------------------- finding clauses ----
    policy.status = STATUS_FINDING_CLAUSES
    await db.flush()

    segmented = segment(pages)
    clause_rows: dict[int, PolicyClause] = {}
    for clause in segmented:
        row = PolicyClause(
            policy_id=policy.id,
            document_id=document.id,
            clause_type=clause.clause_type,
            title=clause.title,
            source_page=clause.source_page,
            source_text=clause.source_text,
            normalized_text=clause.normalized_text,
            ordinal=clause.ordinal,
        )
        db.add(row)
        clause_rows[clause.ordinal] = row
    await db.flush()

    # ----------------------------------------------- structured extraction --
    policy.status = STATUS_BUILDING_SUMMARY
    await db.flush()

    facts = extractor.extract(segmented)
    found = 0
    not_found = 0
    for fact in facts:
        if fact.value is None:
            not_found += 1
        else:
            found += 1
        clause_row = (
            clause_rows.get(fact.clause_ordinal) if fact.clause_ordinal is not None else None
        )
        db.add(
            PolicyFact(
                policy_id=policy.id,
                extraction_run_id=run.id,
                fact_key=fact.fact_key,
                value_json=fact.value,
                confidence=fact.confidence,
                confidence_state=fact.confidence_state,
                clause_id=clause_row.id if clause_row is not None else None,
                source_page=fact.source_page,
                source_quote=fact.source_quote,
                alternatives_json=fact.alternatives,
            )
        )

    # ------------------------------------------------------------- ready ----
    # Q&A retrieval is Phase 13. The stage is passed through rather than
    # skipped so the reader sees the sequence the product promised, and it
    # completes immediately because there is genuinely nothing to prepare yet.
    policy.status = STATUS_PREPARING_QA
    await db.flush()

    run.status = RUN_SUCCEEDED
    run.completed_at = utcnow()
    policy.status = STATUS_READY
    policy.ready_at = utcnow()
    await analytics.record_safely(
        db,
        name=POLICY_PROCESSING_COMPLETED,
        properties={"facts_found": found, "facts_not_found": not_found, "outcome": "READY"},
    )
    await db.commit()

    logger.info(
        "policy_processing_completed",
        extra=log_fields(
            event="policy_processing_completed",
            resource_type="uploaded_policy",
            resource_id=policy.id,
        ),
    )

    return ExtractionResult(
        run_id=run.id,
        pages=len(pages),
        clauses=len(segmented),
        facts_found=found,
        facts_not_found=not_found,
    )


#: Failures that will produce the same result on every attempt. Retrying an
#: encrypted PDF three times only delays telling the reader something they
#: could act on immediately.
PERMANENT_FAILURES = frozenset(
    {"ENCRYPTED_PDF", "CORRUPT_PDF", "SCAN_NEEDS_OCR", "NO_PAGES", "NO_TEXT"}
)


def is_permanent(reason: str) -> bool:
    return reason in PERMANENT_FAILURES
