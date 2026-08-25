"""Question definitions and the branching rules that select them.

The shape follows `QuestionDefinition` in
docs/03_FRONTEND_ARCHITECTURE.md section 3. Two fields are additions, both
recorded in docs/SPEC_ISSUES.md: `maxSelections` (the specification asks for
"choose up to 3" but gives the schema no way to express a limit) and
`sensitive` (docs/05_DATA_MODEL.md section 2 requires sensitive fields to be
flagged in metadata).

Branching is deterministic and data-driven. There is no expression language
here on purpose: a condition is a small, inspectable structure, so which
questions a person saw can be reconstructed exactly from their stored answers.
"""

from __future__ import annotations

from typing import Any, Literal, assert_never

from pydantic import BaseModel, ConfigDict, Field

Domain = Literal["HEALTH", "MOTOR"]

InputType = Literal[
    "SINGLE_CHOICE",
    "MULTI_CHOICE",
    "NUMBER",
    "MONEY",
    "PINCODE",
    "BOOLEAN",
]

Operator = Literal["EQUALS", "NOT_EQUALS", "IN"]


class Condition(BaseModel):
    """`showIf`: a question appears only when this holds.

    `all_of` composes conditions with AND. That is the only combinator, which
    keeps every branch trivially explainable to a user who asks why they were
    asked something.
    """

    model_config = ConfigDict(frozen=True)

    field: str | None = None
    operator: Operator | None = None
    value: Any = None
    all_of: tuple[Condition, ...] = ()

    def evaluate(self, answers: dict[str, Any]) -> bool:
        if self.all_of:
            return all(condition.evaluate(answers) for condition in self.all_of)

        if self.field is None or self.operator is None:
            # A condition with nothing to test shows the question.
            return True

        actual = answers.get(self.field)
        match self.operator:
            case "EQUALS":
                return bool(actual == self.value)
            case "NOT_EQUALS":
                return bool(actual != self.value)
            case "IN":
                return actual in (self.value or [])
            case _:  # pragma: no cover - exhaustive over Operator
                assert_never(self.operator)


Condition.model_rebuild()


class Option(BaseModel):
    model_config = ConfigDict(frozen=True)

    value: str
    label: str
    description: str | None = None


class Stage(BaseModel):
    """A named group of questions, shown as progress (docs/02_UX_UI_SPEC.md section 7)."""

    model_config = ConfigDict(frozen=True)

    key: str
    label: str


class QuestionDefinition(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    stage: str
    title: str
    description: str | None = None
    input_type: InputType
    options: tuple[Option, ...] = ()
    required: bool = True
    show_if: Condition | None = None
    data_field: str
    #: Static answer to "Why we're asking this" (docs/02_UX_UI_SPEC.md rule 3).
    help_text: str | None = None
    analytics_key: str
    #: MULTI_CHOICE only. "Choose up to 3 things that matter most."
    max_selections: int | None = None
    #: Never send this answer's value to analytics or logs.
    sensitive: bool = False
    unit: str | None = None
    min_value: int | None = None
    max_value: int | None = None


class QuestionnaireDefinition(BaseModel):
    """One immutable, versioned question set."""

    model_config = ConfigDict(frozen=True)

    domain: Domain
    version: str
    #: DRAFT until the founder's wording pass
    #: (docs/13_DECISIONS_AND_OPEN_ITEMS.md open item 6).
    status: Literal["DRAFT", "ACTIVE"] = "DRAFT"
    stages: tuple[Stage, ...] = Field(default=())
    questions: tuple[QuestionDefinition, ...] = Field(default=())

    def question(self, question_id: str) -> QuestionDefinition | None:
        return next((q for q in self.questions if q.id == question_id), None)

    def visible_questions(self, answers: dict[str, Any]) -> list[QuestionDefinition]:
        """The questions this person should see, given what they have answered.

        Recomputed from scratch every time rather than stored: the answers are
        the source of truth, so a changed answer cannot leave a stale branch
        behind.
        """
        return [
            question
            for question in self.questions
            if question.show_if is None or question.show_if.evaluate(answers)
        ]

    def stage_of(self, question: QuestionDefinition) -> Stage | None:
        return next((stage for stage in self.stages if stage.key == question.stage), None)
