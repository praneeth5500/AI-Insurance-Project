"""Answer validation.

Every answer is checked against its question definition before it is stored,
so a draft can never hold a value the questionnaire could not have produced.
The error message never echoes the submitted value: answers can be sensitive.
"""

from __future__ import annotations

import re
from typing import Any

from app.questionnaires.definitions import QuestionDefinition
from app.questionnaires.errors import InvalidAnswerError

PINCODE_PATTERN = re.compile(r"^\d{6}$")


def _reject(reason: str) -> None:
    raise InvalidAnswerError(reason)


def validate_answer(question: QuestionDefinition, value: Any) -> Any:
    """Return the normalised value, or raise InvalidAnswerError."""
    if value is None or value == "" or value == []:
        if question.required:
            _reject("This question needs an answer.")
        return None

    if question.input_type == "SINGLE_CHOICE":
        allowed = {option.value for option in question.options}
        if not isinstance(value, str) or value not in allowed:
            _reject("Choose one of the options shown.")
        return value

    if question.input_type == "MULTI_CHOICE":
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            _reject("Choose from the options shown.")
        allowed = {option.value for option in question.options}
        if any(item not in allowed for item in value):
            _reject("Choose from the options shown.")
        if len(set(value)) != len(value):
            _reject("Each option can only be chosen once.")
        if question.max_selections is not None and len(value) > question.max_selections:
            _reject(f"Choose up to {question.max_selections}.")
        # Preserve the order they were chosen in; it becomes rank order.
        return list(value)

    if question.input_type == "BOOLEAN":
        if not isinstance(value, bool):
            _reject("Answer yes or no.")
        return value

    if question.input_type in ("NUMBER", "MONEY"):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            _reject("Enter a number.")
        number = int(value)
        if number != value:
            _reject("Enter a whole number.")
        if question.min_value is not None and number < question.min_value:
            _reject(f"Enter {question.min_value} or more.")
        if question.max_value is not None and number > question.max_value:
            _reject(f"Enter {question.max_value} or less.")
        return number

    if question.input_type == "PINCODE":
        if not isinstance(value, str) or not PINCODE_PATTERN.match(value):
            _reject("Enter all 6 digits of your pincode.")
        return value

    _reject("That answer isn't valid for this question.")
    return None  # pragma: no cover - _reject always raises
