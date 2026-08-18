from __future__ import annotations

from dataclasses import dataclass
import re

from simulation.conversation.ledger import ConversationLanguageContext, ProductLanguageContext
from simulation.conversation.models import ConversationPair, ConversationResult
from simulation.product.text_evidence import normalize_evidence_text


@dataclass(frozen=True, slots=True)
class LanguageValidationIssue:
    code: str
    speaker_label: str
    detail: str


@dataclass(frozen=True, slots=True)
class LanguageValidationResult:
    valid: bool
    issues: tuple[LanguageValidationIssue, ...]


_INTERNAL_TERMS = (
    "income score",
    "argument strength",
    "confidence score",
    "affordability score",
    "price context",
    "price pressure",
    "stance band",
    "technology adoption",
    "brand loyalty",
    "product need",
    "agent traits",
    "social susceptibility",
    "risk tolerance score",
)
_SPEAKER_ARTIFACT_RE = re.compile(r"(?:^|\s)(?:a\s*\|\s*b|b\s*\|\s*a|agent\s+[ab])\s*:", re.IGNORECASE)
_DEMOGRAPHIC_AFFORDABILITY_RE = re.compile(
    r"\b(?:student|teacher|doctor|nurse|engineer|worker|professional|entrepreneur)\b.{0,60}\b(?:afford|budget|income|too expensive|cheap)\b"
    r"|\b(?:afford|budget|income|too expensive|cheap)\b.{0,60}\b(?:student|teacher|doctor|nurse|engineer|worker|professional|entrepreneur)\b",
    re.IGNORECASE,
)

_UNSUPPORTED_FACT_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("reviews", re.compile(r"\breviews?\b", re.IGNORECASE)),
    ("competitor", re.compile(r"\bcompetitors?\b|\bother brands?\b", re.IGNORECASE)),
    ("free alternatives", re.compile(r"\bfree alternatives?\b|\bfree options?\b", re.IGNORECASE)),
    ("market average", re.compile(r"\bmarket averages?\b|\bindustry averages?\b", re.IGNORECASE)),
    ("discount", re.compile(r"\bdiscounts?\b|\bpromo(?:tion)?s?\b", re.IGNORECASE)),
    ("trial", re.compile(r"\bfree trials?\b|\btrial period\b", re.IGNORECASE)),
    ("warranty", re.compile(r"\bwarrant(?:y|ies)\b", re.IGNORECASE)),
)

_TOPIC_POSITIVE_PATTERNS: dict[str, tuple[re.Pattern[str], ...]] = {
    "price": (
        re.compile(r"\b(?:cheap|affordable|reasonable price|fair price|good value|great deal|bargain)\b", re.IGNORECASE),
    ),
    "trust": (
        re.compile(r"\b(?:completely trust|fully trust|very credible|highly credible|no doubts?)\b", re.IGNORECASE),
    ),
    "quality": (
        re.compile(r"\b(?:excellent quality|very reliable|high quality|well built)\b", re.IGNORECASE),
    ),
    "privacy": (
        re.compile(r"\b(?:privacy is excellent|very private|privacy is strong|no privacy concern)\b", re.IGNORECASE),
    ),
}
_TOPIC_NEGATIVE_PATTERNS: dict[str, tuple[re.Pattern[str], ...]] = {
    "price": (
        re.compile(r"\b(?:too expensive|very expensive|overpriced|too costly|price is steep|cost is steep|cannot justify the cost|can't justify the cost)\b", re.IGNORECASE),
    ),
    "trust": (
        re.compile(r"\b(?:do not trust|don't trust|completely distrust|not credible|very suspicious|not convinced at all)\b", re.IGNORECASE),
    ),
    "quality": (
        re.compile(r"\b(?:very poor quality|terrible quality|completely unreliable|badly built)\b", re.IGNORECASE),
    ),
    "privacy": (
        re.compile(r"\b(?:serious privacy problem|major privacy risk|privacy is terrible|no privacy at all)\b", re.IGNORECASE),
    ),
}


def validate_rendered_conversation(
    transcript: list[dict[str, str | int]],
    *,
    semantic_result: ConversationResult,
    pair: ConversationPair,
    language_context: ConversationLanguageContext,
    product_context: ProductLanguageContext | None,
) -> LanguageValidationResult:
    del language_context  # Identity is non-authoritative for semantic validation.
    issues: list[LanguageValidationIssue] = []
    product_text = _product_text(product_context)

    for index, item in enumerate(transcript):
        text = str(item.get("text", ""))
        speaker_label = _speaker_label(item.get("speaker_id"), pair)
        normalized = normalize_evidence_text(text)

        for term in _INTERNAL_TERMS:
            if term in normalized:
                issues.append(LanguageValidationIssue("internal_state_leak", speaker_label, term))
                break

        if _SPEAKER_ARTIFACT_RE.search(text):
            issues.append(LanguageValidationIssue("speaker_artifact", speaker_label, "visible renderer speaker label"))

        if _DEMOGRAPHIC_AFFORDABILITY_RE.search(text):
            issues.append(
                LanguageValidationIssue(
                    "demographic_affordability",
                    speaker_label,
                    "affordability inferred from occupation/demographic label",
                )
            )

        unsupported = _unsupported_fact(text, product_text)
        if unsupported is not None:
            issues.append(LanguageValidationIssue("unsupported_external_fact", speaker_label, unsupported))

        if index < len(semantic_result.messages):
            semantic_issue = _semantic_direction_issue(text, semantic_result.messages[index].topic_effects)
            if semantic_issue is not None:
                issues.append(
                    LanguageValidationIssue(
                        "semantic_direction_contradiction",
                        speaker_label,
                        semantic_issue,
                    )
                )

    return LanguageValidationResult(valid=not issues, issues=tuple(issues))


def _speaker_label(speaker_id: object, pair: ConversationPair) -> str:
    if speaker_id == pair.agent_a_id:
        return "A"
    if speaker_id == pair.agent_b_id:
        return "B"
    return "?"


def _product_text(product: ProductLanguageContext | None) -> str:
    if product is None:
        return ""
    return normalize_evidence_text(
        " ".join(
            (
                product.name,
                product.category,
                product.pitch_excerpt,
            )
        )
    )


def _unsupported_fact(text: str, product_text: str) -> str | None:
    for label, pattern in _UNSUPPORTED_FACT_PATTERNS:
        if pattern.search(text) and not pattern.search(product_text):
            return label
    return None


def _semantic_direction_issue(text: str, topic_effects: dict[str, float]) -> str | None:
    if not topic_effects:
        return None
    topic, stance = max(topic_effects.items(), key=lambda item: abs(float(item[1])))
    stance_value = float(stance)
    if abs(stance_value) < 0.35:
        return None

    positive = any(pattern.search(text) for pattern in _TOPIC_POSITIVE_PATTERNS.get(topic, ()))
    negative = any(pattern.search(text) for pattern in _TOPIC_NEGATIVE_PATTERNS.get(topic, ()))
    if stance_value >= 0.35 and negative and not positive:
        return f"positive {topic} stance rendered with strongly negative wording"
    if stance_value <= -0.35 and positive and not negative:
        return f"negative {topic} stance rendered with strongly positive wording"
    return None
