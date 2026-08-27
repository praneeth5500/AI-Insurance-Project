"""What can go on a claims checklist, and where each item is allowed to come
from.

`docs/07_POLICY_DECODER_AI.md` section 10 permits exactly three sources:
relevant source clauses, approved general process templates, and clearly
labelled assumptions. This module holds the second and third; the first is
derived from the reader's own document in `service.py`.

The general items below are the approved templates. Two rules govern them:

* **They describe what insurers commonly ask for, not what this policy
  requires.** They are grouped separately and labelled "Not from your policy"
  wherever they appear. Presenting one as a policy requirement would be
  inventing a term the document does not contain.
* **They are procedural, never predictive.** Nothing here says a claim will
  be paid, or is more likely to be paid, if the reader does these things.
  `docs/01_PRODUCT_SPEC.md` section 3.6: the beta does not predict claim
  approval, and "do this and you'll be fine" is that prediction wearing a
  checklist.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.claims.models import ORIGIN_CONFIRM_WITH_INSURER, ORIGIN_GENERAL_PREPARATION


@dataclass(frozen=True)
class TemplateItem:
    key: str
    label: str
    description: str
    origin: str


#: Approved general process templates. Ordered as someone would actually work
#: through them: identify yourself, then the treatment, then the money.
GENERAL_PREPARATION: tuple[TemplateItem, ...] = (
    TemplateItem(
        key="policy_number",
        label="Your policy number and the insurer's claims phone number",
        description=(
            "Keep both somewhere you can reach without the document — a photo on your phone "
            "is enough. At a hospital admission desk this is usually the first thing asked."
        ),
        origin=ORIGIN_GENERAL_PREPARATION,
    ),
    TemplateItem(
        key="id_proof",
        label="Photo ID for everyone on the policy",
        description=(
            "Insurers generally ask for identification matching the names on the policy. "
            "Having it ready for each person covered avoids a delay at the worst moment."
        ),
        origin=ORIGIN_GENERAL_PREPARATION,
    ),
    TemplateItem(
        key="doctor_documents",
        label="The doctor's prescription, diagnosis and advice for admission",
        description=(
            "Claims are normally assessed against what the treating doctor wrote. Ask for "
            "copies at the time — they are much harder to obtain weeks later."
        ),
        origin=ORIGIN_GENERAL_PREPARATION,
    ),
    TemplateItem(
        key="bills_and_reports",
        label="Itemised hospital bill, payment receipts and test reports",
        description=(
            "An itemised bill — not a summary — plus the reports behind each charge. "
            "Reimbursement claims are commonly held up for exactly this."
        ),
        origin=ORIGIN_GENERAL_PREPARATION,
    ),
    TemplateItem(
        key="bank_details",
        label="Bank account details for reimbursement",
        description=(
            "For anything you pay yourself, the money comes back by transfer. Having the "
            "account details and a cancelled cheque ready saves a round trip."
        ),
        origin=ORIGIN_GENERAL_PREPARATION,
    ),
)

#: Things a policy document routinely leaves out, which the reader can only
#: get from the insurer. Offered as questions, never as answers — an assumed
#: notification window is an invented policy term.
CONFIRM_WITH_INSURER: tuple[TemplateItem, ...] = (
    TemplateItem(
        key="notification_window",
        label="How soon you must tell them about a claim",
        description=(
            "Many policies require notice within a set number of hours of admission, and "
            "missing it can affect the claim. If your document doesn't state a window, ask "
            "for it in writing."
        ),
        origin=ORIGIN_CONFIRM_WITH_INSURER,
    ),
    TemplateItem(
        key="cashless_process",
        label="Exactly how to arrange cashless treatment",
        description=(
            "Who to call, what the hospital needs from you, and how long approval usually "
            "takes. Worth knowing before an admission rather than during one."
        ),
        origin=ORIGIN_CONFIRM_WITH_INSURER,
    ),
    TemplateItem(
        key="network_hospitals",
        label="Which hospitals near you are in the network",
        description=(
            "Network lists change, and the version in a policy document is out of date the "
            "day it is printed. Check the current list for the hospitals you would actually "
            "use."
        ),
        origin=ORIGIN_CONFIRM_WITH_INSURER,
    ),
)


def general_items() -> tuple[TemplateItem, ...]:
    return GENERAL_PREPARATION


def insurer_questions() -> tuple[TemplateItem, ...]:
    return CONFIRM_WITH_INSURER
