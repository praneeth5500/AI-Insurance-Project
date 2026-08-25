"""Questionnaire payloads (docs/08_API_CONTRACTS.md section 3).

The response carries the *visible* question list as well as the answers, so
the renderer never has to know which questions exist or how branching works —
that stays on the server, where a completed session can be replayed exactly.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from app.core.schema import ApiModel
from app.questionnaires.definitions import (
    InputType,
    QuestionDefinition,
    QuestionnaireDefinition,
)
from app.questionnaires.service import SessionState


class OptionView(ApiModel):
    value: str
    label: str
    description: str | None = None


class QuestionView(ApiModel):
    id: str
    stage: str
    title: str
    description: str | None = None
    input_type: InputType
    options: list[OptionView] = []
    required: bool
    data_field: str
    #: "Why we're asking this" (docs/02_UX_UI_SPEC.md rule 3).
    help_text: str | None = None
    max_selections: int | None = None
    unit: str | None = None
    min_value: int | None = None
    max_value: int | None = None
    #: True when the answer must never reach analytics or logs.
    sensitive: bool

    @classmethod
    def of(cls, question: QuestionDefinition) -> QuestionView:
        return cls(
            id=question.id,
            stage=question.stage,
            title=question.title,
            description=question.description,
            input_type=question.input_type,
            options=[
                OptionView(value=o.value, label=o.label, description=o.description)
                for o in question.options
            ],
            required=question.required,
            data_field=question.data_field,
            help_text=question.help_text,
            max_selections=question.max_selections,
            unit=question.unit,
            min_value=question.min_value,
            max_value=question.max_value,
            sensitive=question.sensitive,
        )


class StageView(ApiModel):
    key: str
    label: str
    #: Ids of the questions currently visible in this stage.
    question_ids: list[str] = []
    complete: bool


class AnswerView(ApiModel):
    question_id: str
    value: Any


class CreateSessionRequest(ApiModel):
    domain: Literal["HEALTH", "MOTOR"] = "HEALTH"


class SaveAnswerRequest(ApiModel):
    value: Any = None


class SessionView(ApiModel):
    id: str
    domain: str
    questionnaire_version: str
    status: str
    started_at: datetime
    completed_at: datetime | None = None
    #: DRAFT until the founder's wording pass on the question set.
    definition_status: str
    stages: list[StageView]
    questions: list[QuestionView]
    answers: list[AnswerView]
    current_stage: str | None = None
    next_question_id: str | None = None
    is_complete: bool

    @classmethod
    def of(cls, state: SessionState) -> SessionView:
        definition: QuestionnaireDefinition = state.definition
        answered = {
            question.id: state.answers.get(question.data_field)
            for question in state.visible
            if state.answers.get(question.data_field) is not None
        }

        stages: list[StageView] = []
        for stage in definition.stages:
            in_stage = [q for q in state.visible if q.stage == stage.key]
            stages.append(
                StageView(
                    key=stage.key,
                    label=stage.label,
                    question_ids=[q.id for q in in_stage],
                    complete=all(
                        not q.required or state.answers.get(q.data_field) is not None
                        for q in in_stage
                    ),
                )
            )

        next_question = state.next_question

        return cls(
            id=state.session.id,
            domain=state.session.domain,
            questionnaire_version=state.session.questionnaire_version,
            status=state.session.status,
            started_at=state.session.started_at,
            completed_at=state.session.completed_at,
            definition_status=definition.status,
            stages=stages,
            questions=[QuestionView.of(q) for q in state.visible],
            answers=[
                AnswerView(question_id=question_id, value=value)
                for question_id, value in answered.items()
            ],
            current_stage=next_question.stage if next_question else None,
            next_question_id=next_question.id if next_question else None,
            is_complete=state.is_complete,
        )
