"""Finding the clauses a question is actually about.

`docs/07_POLICY_DECODER_AI.md` section 7 puts retrieval before generation and
puts an **evidence-sufficiency check** between them. That check is the reason
this module exists separately: a question the policy does not answer must be
detectable *before* anything tries to answer it, because a model handed weak
evidence will still write a confident paragraph.

Retrieval is deterministic term scoring rather than embeddings. Three reasons:

* the same question must produce the same citations every time, or a reader
  who re-asks gets a different answer to the same words;
* an embedding service is another undecided vendor, and this works without
  one;
* term overlap is inspectable — when retrieval picks the wrong clause you can
  see exactly which words did it, which is not true of a vector.

Scoring is idf-weighted overlap: a term that appears in one clause says much
more about that clause than a term appearing in all of them. That is what
stops "policy", "insured" and "cover" — which are in every clause of every
policy — from dominating.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass

from app.extraction.models import PolicyClause

#: Words too common in insurance prose to carry meaning, plus ordinary English
#: stopwords. Kept explicit rather than pulled from a library: the insurance
#: half is domain judgement and should be visible and editable.
STOPWORDS = frozenset(
    # Ordinary English stopwords.
    [
        "a",
        "an",
        "and",
        "any",
        "are",
        "as",
        "at",
        "be",
        "been",
        "but",
        "by",
        "can",
        "do",
        "does",
        "for",
        "from",
        "has",
        "have",
        "how",
        "i",
        "if",
        "in",
        "is",
        "it",
        "its",
        "me",
        "my",
        "no",
        "not",
        "of",
        "on",
        "or",
        "our",
        "shall",
        "should",
        "so",
        "than",
        "that",
        "the",
        "their",
        "them",
        "then",
        "there",
        "these",
        "they",
        "this",
        "to",
        "under",
        "upon",
        "was",
        "we",
        "were",
        "what",
        "when",
        "where",
        "which",
        "who",
        "will",
        "with",
        "would",
        "you",
        "your",
    ]
    # Words in every clause of every policy. They carry no signal about which
    # clause a question is about, and without them a question made only of
    # these words is correctly recognised as too broad to search on.
    + [
        "policy",
        "policies",
        "insured",
        "insurer",
        "insurance",
        "cover",
        "covered",
        "coverage",
        "company",
        "person",
        "persons",
        "clause",
        "section",
        "terms",
        "condition",
        "conditions",
    ]
)

#: A question that retrieves nothing above this is not answerable from the
#: policy. Deliberately not zero: a single incidental word in common is not
#: evidence, and "I couldn't determine that" is a better answer than a
#: paragraph built on one coincidental match.
MIN_RELEVANCE = 1.2

#: How many clauses an answer may be built from. Enough to cover a question
#: answered in two places; few enough that the reader can check them all.
MAX_EVIDENCE = 3

RETRIEVAL_VERSION = "term-overlap-001"


@dataclass(frozen=True)
class Retrieved:
    clause: PolicyClause
    score: float
    #: Which of the question's terms matched. Shown in nothing, used in
    #: everything: this is what makes a bad retrieval diagnosable.
    matched_terms: tuple[str, ...]


def tokenize(text: str) -> list[str]:
    return [
        token
        for token in re.findall(r"[a-z]+", text.lower())
        if len(token) > 2 and token not in STOPWORDS
    ]


def _stem(token: str) -> str:
    """A crude suffix trim, so "waiting" matches "wait" and "exclusions"
    matches "exclusion".

    Not a real stemmer. A real one is another dependency and its mistakes are
    harder to reason about than this one's.
    """
    for suffix in ("ations", "ation", "ings", "ing", "ies", "es", "s"):
        if token.endswith(suffix) and len(token) - len(suffix) >= 4:
            return token[: -len(suffix)]
    return token


def retrieve(question: str, clauses: list[PolicyClause]) -> list[Retrieved]:
    """The clauses most likely to answer this question, best first."""
    if not clauses:
        return []

    question_terms = {_stem(token) for token in tokenize(question)}
    if not question_terms:
        return []

    documents = [
        Counter(
            _stem(token)
            for token in tokenize(
                f"{clause.title or ''} {clause.normalized_text or clause.source_text}"
            )
        )
        for clause in clauses
    ]

    total = len(documents)
    document_frequency: Counter[str] = Counter()
    for counts in documents:
        for term in counts:
            document_frequency[term] += 1

    scored: list[Retrieved] = []
    for clause, counts in zip(clauses, documents, strict=True):
        score = 0.0
        matched: list[str] = []
        for term in question_terms:
            occurrences = counts.get(term, 0)
            if occurrences == 0:
                continue
            matched.append(term)
            # idf, floored at zero so a term in every clause contributes
            # nothing rather than going negative.
            idf = (
                max(math.log(total / document_frequency[term]), 0.0)
                if document_frequency[term]
                else 0.0
            )
            # Diminishing returns on repetition: a clause that says "waiting"
            # six times is not six times more relevant.
            score += (1.0 + math.log(occurrences)) * (idf + 0.3)

        # A clause whose *title* matches is usually the one the reader means.
        if clause.title:
            title_terms = {_stem(token) for token in tokenize(clause.title)}
            score += 1.5 * len(question_terms & title_terms)

        if matched:
            scored.append(
                Retrieved(clause=clause, score=score, matched_terms=tuple(sorted(matched)))
            )

    scored.sort(key=lambda item: (-item.score, item.clause.ordinal))
    return scored


def sufficient(retrieved: list[Retrieved]) -> list[Retrieved]:
    """The evidence-sufficiency check (section 7).

    Returns only clauses strong enough to answer from — empty when the policy
    does not appear to address the question at all. Everything downstream
    depends on this being conservative: an answer built on thin evidence is
    worse than no answer, because the reader cannot tell the difference.
    """
    strong = [item for item in retrieved if item.score >= MIN_RELEVANCE]
    return strong[:MAX_EVIDENCE]
