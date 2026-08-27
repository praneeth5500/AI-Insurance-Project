"""Claims readiness (docs/11_BUILD_PLAN.md Phase 14).

`docs/01_PRODUCT_SPEC.md` section 3.6 draws the line this phase must not
cross: explain claims clauses and build a checklist, but **do not predict
guaranteed claim approval**. `docs/07_POLICY_DECODER_AI.md` section 10 adds
the structural half — three kinds of checklist item, kept apart, never
blended.

Most of these tests are about that separation, because blending is the failure
that turns a helpful checklist into an invented policy term.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.claims import service
from app.claims.models import (
    ORIGIN_CONFIRM_WITH_INSURER,
    ORIGIN_GENERAL_PREPARATION,
    ORIGIN_POLICY_SPECIFIC,
    STATUS_COMPLETED,
)
from app.claims.schemas import ChecklistView
from app.claims.templates import general_items, insurer_questions
from app.core.config import Settings
from app.extraction.pipeline import process_document
from app.jobs.queue import DatabaseJobQueue
from app.policies import service as policy_service
from app.policies.errors import PolicyNotFoundError
from app.policies.storage import LocalFileStorage
from app.users.models import User
from tests.test_extraction import POLICY_TEXT
from tests.test_policy_upload import pdf_bytes
from tests.test_questionnaire import make_user

#: A policy that actually says something about claims, so the
#: policy-specific group is exercised rather than assumed empty.
CLAIMS_POLICY = (
    POLICY_TEXT.strip()
    + """
SECTION 6 - CLAIM PROCEDURE
The insurer must receive intimation of any claim within 24 hours of admission
to a hospital, and the original documents listed in the schedule must be
submitted within 15 days of discharge from that hospital.
Cashless treatment requires pre-authorisation from the insurer before any
planned admission to a network hospital under this contract of insurance.
"""
)


@pytest.fixture
def storage(tmp_path: Path) -> LocalFileStorage:
    return LocalFileStorage(Settings(app_env="local"), root=tmp_path / "uploads")


@pytest.fixture
def settings() -> Settings:
    return Settings(app_env="local", feature_policy_decoder=True)


async def ready_policy(
    db: AsyncSession,
    storage: LocalFileStorage,
    settings: Settings,
    *,
    text: str = CLAIMS_POLICY,
    email: str = "r@example.com",
) -> tuple[User, str]:
    user = await make_user(db, email)
    uploaded = await policy_service.create_policy_from_upload(
        db,
        user=user,
        storage=storage,
        queue=DatabaseJobQueue(db),
        settings=settings,
        filename="wording.pdf",
        data=pdf_bytes(text=text),
    )
    await process_document(
        db, policy_id=uploaded.policy.id, document_id=uploaded.documents[0].id, storage=storage
    )
    return user, uploaded.policy.id


# ---------------------------------------------------- the three groups ---


async def test_a_checklist_keeps_the_three_kinds_of_item_apart(
    db: AsyncSession, storage: LocalFileStorage, settings: Settings
) -> None:
    """docs/07_POLICY_DECODER_AI.md section 10: do not blend them."""
    user, policy_id = await ready_policy(db, storage, settings)

    view = ChecklistView.of(await service.get_or_create(db, user=user, policy_id=policy_id))

    origins = [group.origin for group in view.groups]
    assert ORIGIN_POLICY_SPECIFIC in origins
    assert ORIGIN_GENERAL_PREPARATION in origins
    assert ORIGIN_CONFIRM_WITH_INSURER in origins
    # Each item appears in exactly one group.
    ids = [item.id for group in view.groups for item in group.items]
    assert len(ids) == len(set(ids)) == view.total_count


async def test_every_policy_specific_item_carries_the_clause_it_came_from(
    db: AsyncSession, storage: LocalFileStorage, settings: Settings
) -> None:
    """An item claiming to come from the policy without a clause behind it is
    an invented policy term."""
    user, policy_id = await ready_policy(db, storage, settings)

    view = ChecklistView.of(await service.get_or_create(db, user=user, policy_id=policy_id))
    specific = next(g for g in view.groups if g.origin == ORIGIN_POLICY_SPECIFIC)

    assert specific.items
    for item in specific.items:
        assert item.source is not None, item.label
        assert item.source.page >= 1
        assert item.source.clause_text


async def test_general_items_never_claim_to_come_from_the_policy(
    db: AsyncSession, storage: LocalFileStorage, settings: Settings
) -> None:
    user, policy_id = await ready_policy(db, storage, settings)

    view = ChecklistView.of(await service.get_or_create(db, user=user, policy_id=policy_id))

    for origin in (ORIGIN_GENERAL_PREPARATION, ORIGIN_CONFIRM_WITH_INSURER):
        group = next(g for g in view.groups if g.origin == origin)
        for item in group.items:
            assert item.source is None, item.label


async def test_the_general_group_says_what_it_is_not(
    db: AsyncSession, storage: LocalFileStorage, settings: Settings
) -> None:
    """A group heading that blurred this would undo the separation."""
    user, policy_id = await ready_policy(db, storage, settings)

    view = ChecklistView.of(await service.get_or_create(db, user=user, policy_id=policy_id))
    general = next(g for g in view.groups if g.origin == ORIGIN_GENERAL_PREPARATION)

    assert "Not from your policy" in general.explanation
    assert "may not require them" in general.explanation


async def test_a_policy_that_says_nothing_about_claims_gets_no_invented_requirements(
    db: AsyncSession, storage: LocalFileStorage, settings: Settings
) -> None:
    """An empty group is more useful than a plausible one.

    The reader learns their document is silent on this, which is a real and
    actionable fact about their policy.
    """
    user, policy_id = await ready_policy(db, storage, settings, text=POLICY_TEXT.strip())

    view = ChecklistView.of(await service.get_or_create(db, user=user, policy_id=policy_id))

    assert all(group.origin != ORIGIN_POLICY_SPECIFIC for group in view.groups)
    # The reader is not left with nothing: the other two groups still apply.
    assert view.total_count == len(general_items()) + len(insurer_questions())


# ------------------------------------------------------- no prediction ---


async def test_nothing_predicts_a_claim_outcome(
    db: AsyncSession, storage: LocalFileStorage, settings: Settings
) -> None:
    """docs/01_PRODUCT_SPEC.md section 3.6 and section 9 of the AI spec."""
    user, policy_id = await ready_policy(db, storage, settings)

    text = (
        ChecklistView.of(await service.get_or_create(db, user=user, policy_id=policy_id))
        .model_dump_json()
        .lower()
    )

    for forbidden in (
        "will be approved",
        "guarantee",
        "guaranteed",
        "your claim will",
        "ensures payment",
        "you will be paid",
    ):
        assert forbidden not in text or "doesn't guarantee" in text


async def test_the_checklist_states_its_own_limits(
    db: AsyncSession, storage: LocalFileStorage, settings: Settings
) -> None:
    user, policy_id = await ready_policy(db, storage, settings)

    view = ChecklistView.of(await service.get_or_create(db, user=user, policy_id=policy_id))

    assert "doesn't guarantee a claim will be paid" in view.disclaimer
    assert "nothing here predicts" in view.disclaimer


def test_general_templates_are_procedural_never_predictive() -> None:
    """ "Do this and you'll be fine" is a claim prediction wearing a
    checklist."""
    for template in (*general_items(), *insurer_questions()):
        lowered = f"{template.label} {template.description}".lower()
        for forbidden in ("guarantee", "will be approved", "ensures", "you will be paid"):
            assert forbidden not in lowered, template.key


# ---------------------------------------------------------- ticking off ---


async def test_an_item_can_be_marked_complete_and_stays_that_way(
    db: AsyncSession, storage: LocalFileStorage, settings: Settings
) -> None:
    user, policy_id = await ready_policy(db, storage, settings)
    checklist = await service.get_or_create(db, user=user, policy_id=policy_id)
    first = checklist.items[0].item

    await service.update_item(db, user=user, policy_id=policy_id, item_id=first.id, completed=True)

    reloaded = await service.get_or_create(db, user=user, policy_id=policy_id)
    assert next(e for e in reloaded.items if e.item.id == first.id).item.completed is True
    assert reloaded.completed_count == 1


async def test_a_note_can_be_attached_and_is_bounded(
    db: AsyncSession, storage: LocalFileStorage, settings: Settings
) -> None:
    user, policy_id = await ready_policy(db, storage, settings)
    checklist = await service.get_or_create(db, user=user, policy_id=policy_id)
    item = checklist.items[0].item

    await service.update_item(db, user=user, policy_id=policy_id, item_id=item.id, note="x" * 5000)

    reloaded = await service.get_or_create(db, user=user, policy_id=policy_id)
    note = next(e for e in reloaded.items if e.item.id == item.id).item.user_note
    assert note is not None and len(note) <= service.MAX_NOTE_LENGTH


async def test_the_checklist_is_built_once_and_kept(
    db: AsyncSession, storage: LocalFileStorage, settings: Settings
) -> None:
    """Regenerating on every visit would throw away what the reader ticked."""
    user, policy_id = await ready_policy(db, storage, settings)
    first = await service.get_or_create(db, user=user, policy_id=policy_id)
    await service.update_item(
        db, user=user, policy_id=policy_id, item_id=first.items[0].item.id, completed=True
    )

    second = await service.get_or_create(db, user=user, policy_id=policy_id)

    assert second.session.id == first.session.id
    assert [e.item.id for e in second.items] == [e.item.id for e in first.items]
    assert second.completed_count == 1


async def test_finishing_every_item_completes_the_session(
    db: AsyncSession, storage: LocalFileStorage, settings: Settings
) -> None:
    user, policy_id = await ready_policy(db, storage, settings)
    checklist = await service.get_or_create(db, user=user, policy_id=policy_id)

    for entry in checklist.items:
        result = await service.update_item(
            db, user=user, policy_id=policy_id, item_id=entry.item.id, completed=True
        )

    assert result.session.status == STATUS_COMPLETED


# ------------------------------------------------------ authorization ---


async def test_one_user_cannot_see_another_users_checklist(
    db: AsyncSession, storage: LocalFileStorage, settings: Settings
) -> None:
    _, policy_id = await ready_policy(db, storage, settings, email="owner@example.com")
    intruder = await make_user(db, "intruder@example.com")

    with pytest.raises(PolicyNotFoundError):
        await service.get_or_create(db, user=intruder, policy_id=policy_id)


async def test_an_item_id_from_another_users_checklist_cannot_be_updated(
    db: AsyncSession, storage: LocalFileStorage, settings: Settings
) -> None:
    owner, owner_policy = await ready_policy(db, storage, settings, email="owner@example.com")
    intruder, intruder_policy = await ready_policy(
        db, storage, settings, email="intruder@example.com"
    )
    owner_checklist = await service.get_or_create(db, user=owner, policy_id=owner_policy)
    await service.get_or_create(db, user=intruder, policy_id=intruder_policy)

    with pytest.raises(service.ChecklistItemNotFoundError):
        await service.update_item(
            db,
            user=intruder,
            policy_id=intruder_policy,
            item_id=owner_checklist.items[0].item.id,
            completed=True,
        )


async def test_a_policy_that_is_not_ready_has_no_checklist(
    db: AsyncSession, storage: LocalFileStorage, settings: Settings
) -> None:
    user = await make_user(db)
    uploaded = await policy_service.create_policy_from_upload(
        db,
        user=user,
        storage=storage,
        queue=DatabaseJobQueue(db),
        settings=settings,
        filename="wording.pdf",
        data=pdf_bytes(text=CLAIMS_POLICY),
    )

    with pytest.raises(PolicyNotFoundError):
        await service.get_or_create(db, user=user, policy_id=uploaded.policy.id)
