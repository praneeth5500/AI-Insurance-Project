"""The analytics event registry.

`docs/03_FRONTEND_ARCHITECTURE.md` section 7 lists the events and ends with
the rule that shapes this whole module:

> Never put sensitive medical answer content directly into analytics event
> properties.

`CLAUDE.md` says the same thing more broadly, and the beta checklist asks for
"no sensitive health answers in analytics" as a shippable property. A rule
stated in a comment is one that gets broken; this is enforced the way
`ALLOWED_LOG_FIELDS` enforces the logging rule — **an allow-list, applied
centrally**, so the failure mode is a dropped property rather than a leak.

Two properties fall out of that design:

* An event name that is not declared here is refused. A typo'd event is a
  silent hole in a funnel, and an undeclared event from a client is an
  unbounded write.
* A property key that is not declared for that event is dropped. There is no
  free-form property bag anywhere, which is what makes "no answer values in
  analytics" checkable rather than merely intended.

What may be recorded is deliberately dull: which screen, which step, how many,
which stable identifier. Never what someone answered.
"""

from __future__ import annotations

from dataclasses import dataclass, field

#: Funnel and interaction events. The union of the two specification lists —
#: `docs/03_FRONTEND_ARCHITECTURE.md` section 7 and the analytics section of
#: `docs/12_BETA_CHECKLIST.md`.
HOME_VIEWED = "home_viewed"
RECOMMENDATION_STARTED = "recommendation_started"
QUESTION_ANSWERED = "question_answered"
QUESTION_HELP_OPENED = "question_help_opened"
QUESTIONNAIRE_REVIEWED = "questionnaire_reviewed"
QUESTIONNAIRE_COMPLETED = "questionnaire_completed"
RECOMMENDATION_GENERATED = "recommendation_generated"
MATCH_OPENED = "match_opened"
PRIORITY_CHANGED = "priority_changed"
COMPARE_ADDED = "compare_added"
COMPARISON_VIEWED = "comparison_viewed"
POLICY_UPLOAD_STARTED = "policy_upload_started"
POLICY_UPLOAD_COMPLETED = "policy_upload_completed"
POLICY_PROCESSING_COMPLETED = "policy_processing_completed"
DECODER_SECTION_OPENED = "decoder_section_opened"
POLICY_QUESTION_ASKED = "policy_question_asked"
CITATION_OPENED = "citation_opened"
CLAIMS_CHECKLIST_OPENED = "claims_checklist_opened"
FEEDBACK_SUBMITTED = "feedback_submitted"
ERROR_SHOWN = "error_shown"


@dataclass(frozen=True)
class EventDefinition:
    name: str
    #: What the event is for, so a future reader can tell whether a new
    #: property belongs on it.
    purpose: str
    #: The only property keys this event may carry. Everything else is
    #: dropped before the event is stored.
    allowed_properties: frozenset[str] = field(default_factory=frozenset)
    #: True for events a browser may post. Server-only events cannot be
    #: forged by a client into a funnel.
    client_emittable: bool = False


#: Property keys that are safe on any event: identifiers we generated, and
#: counts. Note what is absent — no answer values, no free text, no filename,
#: no policy content, no email.
_COMMON = frozenset({"domain"})

EVENTS: dict[str, EventDefinition] = {
    definition.name: definition
    for definition in (
        EventDefinition(
            HOME_VIEWED,
            "Did the signed-in home screen get seen at all.",
            _COMMON | {"is_returning"},
            client_emittable=True,
        ),
        EventDefinition(
            RECOMMENDATION_STARTED,
            "Someone began the questionnaire.",
            _COMMON,
        ),
        EventDefinition(
            QUESTION_ANSWERED,
            "Progress through the questionnaire, for drop-off analysis.",
            # The question's id and its stage — never the answer. That
            # distinction is the entire point of this event's shape.
            _COMMON | {"question_id", "stage"},
            client_emittable=True,
        ),
        EventDefinition(
            QUESTION_HELP_OPENED,
            "Which questions people need help understanding.",
            _COMMON | {"question_id"},
            client_emittable=True,
        ),
        EventDefinition(
            QUESTIONNAIRE_REVIEWED,
            "Reached the review screen. Distinct from completing it: docs/SPEC_ISSUES.md issue 3.",
            _COMMON,
            client_emittable=True,
        ),
        EventDefinition(
            QUESTIONNAIRE_COMPLETED,
            "Submitted the questionnaire. The funnel step the beta checklist asks for.",
            _COMMON,
        ),
        EventDefinition(
            RECOMMENDATION_GENERATED,
            "A match set was produced, and how many options it held.",
            _COMMON | {"match_count", "excluded_count", "scoring_version"},
        ),
        EventDefinition(
            MATCH_OPENED,
            "Someone opened an option in full.",
            _COMMON | {"position"},
            client_emittable=True,
        ),
        EventDefinition(
            PRIORITY_CHANGED,
            "Priorities were edited, and how many are now chosen. Never "
            "which ones: a priority is something the reader told us about "
            "themselves.",
            _COMMON | {"priority_count"},
        ),
        EventDefinition(
            COMPARE_ADDED,
            "An option was added to the comparison tray.",
            _COMMON | {"selected_count"},
            client_emittable=True,
        ),
        EventDefinition(
            COMPARISON_VIEWED,
            "A comparison was opened, and of how many options.",
            _COMMON | {"option_count"},
            client_emittable=True,
        ),
        EventDefinition(
            POLICY_UPLOAD_STARTED,
            "Someone reached the upload screen.",
            _COMMON,
            client_emittable=True,
        ),
        EventDefinition(
            POLICY_UPLOAD_COMPLETED,
            "A file was accepted. Never its name, size or type in a way "
            "that could identify the document.",
            _COMMON | {"page_count"},
        ),
        EventDefinition(
            POLICY_PROCESSING_COMPLETED,
            "Extraction finished, and how much it could determine.",
            _COMMON | {"facts_found", "facts_not_found", "outcome"},
        ),
        EventDefinition(
            DECODER_SECTION_OPENED,
            "Which parts of the report people actually read.",
            _COMMON | {"section"},
            client_emittable=True,
        ),
        EventDefinition(
            POLICY_QUESTION_ASKED,
            "A question was asked, and what kind of answer it got. Never the question text.",
            _COMMON | {"answer_state"},
        ),
        EventDefinition(
            CITATION_OPENED,
            "Someone checked the source wording — the trust behaviour this "
            "product is built around.",
            _COMMON | {"context"},
            client_emittable=True,
        ),
        EventDefinition(
            CLAIMS_CHECKLIST_OPENED,
            "The claims checklist was opened.",
            _COMMON | {"item_count"},
            client_emittable=True,
        ),
        EventDefinition(
            FEEDBACK_SUBMITTED,
            "Feedback was left. The comment itself is stored with the "
            "feedback, never on the event.",
            _COMMON | {"context_type", "rating"},
        ),
        EventDefinition(
            ERROR_SHOWN,
            "An error reached a screen. Error telemetry, per Phase 15.",
            _COMMON | {"error_code", "context"},
            client_emittable=True,
        ),
    )
}

#: Every event the beta checklist names, so a missing one fails a test rather
#: than being noticed after launch.
BETA_CHECKLIST_EVENTS: tuple[str, ...] = (
    RECOMMENDATION_STARTED,
    QUESTIONNAIRE_COMPLETED,
    RECOMMENDATION_GENERATED,
    PRIORITY_CHANGED,
    COMPARISON_VIEWED,
    MATCH_OPENED,
    POLICY_UPLOAD_COMPLETED,
    POLICY_PROCESSING_COMPLETED,
    POLICY_QUESTION_ASKED,
    CITATION_OPENED,
    FEEDBACK_SUBMITTED,
)


class UnknownEventError(ValueError):
    """An event name nobody declared."""


def definition_for(name: str) -> EventDefinition:
    definition = EVENTS.get(name)
    if definition is None:
        raise UnknownEventError(f"Unknown analytics event: {name}")
    return definition
