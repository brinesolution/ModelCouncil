from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Literal


Polarity = Literal["positive", "negative"]


@dataclass(frozen=True, slots=True)
class EvidenceRule:
    phrase: str
    weight: float
    polarity: Polarity
    blocked_by_prefixes: tuple[str, ...] = ()
    blocked_by_suffixes: tuple[str, ...] = ()


_DEFAULT_PREFIX_BLOCKERS = {
    "no",
    "not",
    "never",
    "without",
    "lack",
    "lacks",
    "lacking",
    "limited",
}
_PREFIX_SCOPE_BOUNDARIES = {"and", "but", "with", "while", "whereas", "though", "however", "yet"}
_DEFAULT_SUFFIX_BLOCKERS = {
    "exclusion",
    "exclusions",
    "excluded",
    "limited",
    "unavailable",
    "unsupported",
    "void",
    "voided",
    "restriction",
    "restrictions",
}


def normalize_evidence_text(text: str) -> str:
    """Return the canonical token form used by both source text and rule phrases."""
    compact = re.sub(r"[^a-z0-9]+", " ", str(text).lower())
    return " ".join(compact.split())


def phrase_is_affirmed(
    text: str,
    phrase: str,
    *,
    prefix_window: int = 3,
    suffix_window: int = 3,
    blocked_by_prefixes: tuple[str, ...] = (),
    blocked_by_suffixes: tuple[str, ...] = (),
) -> bool:
    source_tokens = normalize_evidence_text(text).split()
    phrase_tokens = normalize_evidence_text(phrase).split()
    if not phrase_tokens or len(phrase_tokens) > len(source_tokens):
        return False

    prefix_blockers = _DEFAULT_PREFIX_BLOCKERS | _normalize_blockers(blocked_by_prefixes)
    suffix_blockers = _DEFAULT_SUFFIX_BLOCKERS | _normalize_blockers(blocked_by_suffixes)

    width = len(phrase_tokens)
    for index in range(len(source_tokens) - width + 1):
        if source_tokens[index : index + width] != phrase_tokens:
            continue

        prefix = source_tokens[max(0, index - prefix_window) : index]
        prefix = _tokens_after_last_boundary(prefix)
        suffix = source_tokens[index + width : index + width + suffix_window]
        if prefix_blockers.intersection(prefix):
            continue
        if suffix_blockers.intersection(suffix):
            continue
        return True
    return False


def score_rules(text: str, rules: tuple[EvidenceRule, ...]) -> float:
    total = 0.0
    for rule in rules:
        if rule.polarity not in {"positive", "negative"}:
            raise ValueError(f"Unsupported evidence polarity: {rule.polarity}")
        if phrase_is_affirmed(
            text,
            rule.phrase,
            blocked_by_prefixes=rule.blocked_by_prefixes,
            blocked_by_suffixes=rule.blocked_by_suffixes,
        ):
            total += rule.weight if rule.polarity == "positive" else -rule.weight
    return total


def _tokens_after_last_boundary(tokens: list[str]) -> list[str]:
    last_boundary = -1
    for index, token in enumerate(tokens):
        if token in _PREFIX_SCOPE_BOUNDARIES:
            last_boundary = index
    return tokens[last_boundary + 1 :]


def _normalize_blockers(values: tuple[str, ...]) -> set[str]:
    normalized: set[str] = set()
    for value in values:
        normalized.update(normalize_evidence_text(value).split())
    return normalized
