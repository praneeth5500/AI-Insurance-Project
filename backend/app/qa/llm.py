"""The language-model seam.

`docs/13_DECISIONS_AND_OPEN_ITEMS.md` open item 2 leaves the provider
undecided and requires the architecture to stay replaceable. So this is an
interface and a deliberate refusal.

`docs/07_POLICY_DECODER_AI.md` section 9 lists what a model must never do —
promise a claim outcome, invent insurer behaviour, invent a clause, produce a
premium, give legal interpretation, tell the reader to ignore the wording. The
place to enforce most of that is *what the model is given*: a model handed
only the retrieved clauses, and required to answer from them, cannot invent a
clause. That constraint is built into `answer()`'s signature — there is no way
to call it without evidence.

Until a provider exists, Q&A answers by quoting the policy rather than
paraphrasing it. That is less fluent and completely grounded, and it is
honest about which one it is doing.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class LlmUnavailableError(RuntimeError):
    """No model provider is configured."""


@dataclass(frozen=True)
class GroundedAnswer:
    text: str
    #: Indices into the evidence list that the answer actually used, so a
    #: citation is never attached to a clause the answer ignored.
    used_evidence: tuple[int, ...]


class LlmProvider(Protocol):
    """docs/13_DECISIONS_AND_OPEN_ITEMS.md open item 2."""

    name: str
    model: str
    prompt_version: str

    async def answer(self, *, question: str, evidence: list[str]) -> GroundedAnswer: ...


class UnavailableLlmProvider:
    """The honest default.

    Raising rather than degrading quietly matters here: the caller catches it
    and tells the reader that explanation in plain language is not available
    yet, while still showing them what their policy says. A provider that
    returned a canned sentence would be indistinguishable from a real answer.
    """

    name = "none"
    model = "none"
    prompt_version = "none"

    async def answer(self, *, question: str, evidence: list[str]) -> GroundedAnswer:
        raise LlmUnavailableError(
            "No language-model provider is configured. See open item 2 in "
            "docs/13_DECISIONS_AND_OPEN_ITEMS.md."
        )


def build_llm_provider() -> LlmProvider:
    """Select the model adapter. One function to change when one is chosen."""
    return UnavailableLlmProvider()
