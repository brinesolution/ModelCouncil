from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from simulation.conversation.ledger import AgentLanguageProfile, ConversationLanguageContext
from simulation.conversation.models import ConversationResult


class DialogueShape(StrEnum):
    agreement = "agreement"
    partial_agreement = "partial_agreement"
    challenge = "challenge"
    trade_off = "trade_off"
    concession = "concession"
    uncertainty = "uncertainty"
    priority_comparison = "priority_comparison"


@dataclass(frozen=True, slots=True)
class SpeakingStyle:
    reasoning: str
    social: str
    confidence: str
    detail: str
    receptivity: str


def derive_speaking_style(profile: AgentLanguageProfile) -> SpeakingStyle:
    reasoning_delta = profile.logicality - profile.emotionality
    if profile.logicality >= 0.70 or reasoning_delta >= 0.20:
        reasoning = "analytical"
    elif profile.emotionality >= 0.70 or reasoning_delta <= -0.20:
        reasoning = "intuitive"
    else:
        reasoning = "balanced"

    if profile.sociability >= 0.65:
        social = "sociable"
    elif profile.sociability <= 0.35:
        social = "reserved"
    else:
        social = "balanced"

    if profile.confidence >= 0.65:
        confidence = "assertive"
    elif profile.confidence <= 0.40:
        confidence = "tentative"
    else:
        confidence = "measured"

    if profile.sociability + profile.logicality >= 1.30:
        detail = "elaborative"
    elif profile.sociability <= 0.35:
        detail = "concise"
    else:
        detail = "moderate"

    if profile.stubbornness <= 0.35:
        receptivity = "receptive"
    elif profile.stubbornness >= 0.65:
        receptivity = "resistant"
    else:
        receptivity = "measured"

    return SpeakingStyle(
        reasoning=reasoning,
        social=social,
        confidence=confidence,
        detail=detail,
        receptivity=receptivity,
    )


def derive_dialogue_shape(
    result: ConversationResult,
    context: ConversationLanguageContext,
) -> DialogueShape:
    del context  # Shape is semantic; identity is intentionally non-authoritative here.
    if len(result.messages) < 2:
        return DialogueShape.uncertainty

    first_topic, first_stance = _primary_topic_stance(result.messages[0].topic_effects)
    second_topic, second_stance = _primary_topic_stance(result.messages[1].topic_effects)

    if abs(first_stance) < 0.12 or abs(second_stance) < 0.12:
        return DialogueShape.uncertainty

    same_direction = first_stance * second_stance > 0
    if first_topic == second_topic:
        if same_direction:
            if abs(first_stance - second_stance) >= 0.35:
                return DialogueShape.partial_agreement
            return DialogueShape.agreement
        if min(abs(first_stance), abs(second_stance)) < 0.35:
            return DialogueShape.concession
        return DialogueShape.challenge

    if not same_direction:
        return DialogueShape.trade_off
    if abs(first_stance - second_stance) >= 0.35:
        return DialogueShape.partial_agreement
    return DialogueShape.priority_comparison


def stance_band(value: float) -> str:
    if value <= -0.65:
        return "strong_negative"
    if value <= -0.35:
        return "moderate_negative"
    if value < -0.12:
        return "mild_negative"
    if value <= 0.12:
        return "neutral"
    if value < 0.35:
        return "mild_positive"
    if value < 0.65:
        return "moderate_positive"
    return "strong_positive"


def _primary_topic_stance(topic_effects: dict[str, float]) -> tuple[str, float]:
    if not topic_effects:
        return "general", 0.0
    return max(topic_effects.items(), key=lambda item: abs(float(item[1])))
