from __future__ import annotations

from dataclasses import dataclass

from simulation.conversation.dialogue_realism import derive_speaking_style, stance_band
from simulation.conversation.ledger import AgentLanguageProfile
from simulation.product.pricing import ConsumerPriceContext


@dataclass(frozen=True, slots=True)
class RendererAgentContext:
    occupation_context: str
    locale: str
    reasoning_style: str
    social_style: str
    confidence_band: str
    detail_band: str
    receptivity_band: str
    knowledge_band: str


@dataclass(frozen=True, slots=True)
class RendererPriceContext:
    billing_cadence: str
    category_price_position: str
    stance_band: str


@dataclass(frozen=True, slots=True)
class RendererSemanticTurn:
    speaker: str
    topics: tuple[str, ...]
    stance_band: str
    argument_band: str
    confidence_band: str


def renderer_agent_context(agent: AgentLanguageProfile) -> RendererAgentContext:
    style = derive_speaking_style(agent)
    return RendererAgentContext(
        occupation_context=agent.occupation,
        locale=agent.locale,
        reasoning_style=style.reasoning,
        social_style=style.social,
        confidence_band=style.confidence,
        detail_band=style.detail,
        receptivity_band=style.receptivity,
        knowledge_band=unit_band(agent.knowledge, low=0.25, high=0.60, labels=("low", "moderate", "high")),
    )


def renderer_price_context(price_context: ConsumerPriceContext | None) -> RendererPriceContext | None:
    if price_context is None:
        return None
    return RendererPriceContext(
        billing_cadence=price_context.billing_cadence.value,
        category_price_position=price_context.position.value,
        stance_band=price_context.stance_band.value,
    )


def renderer_semantic_turn(
    *,
    speaker: str,
    topic_effects: dict[str, float],
    argument_strength: float,
    confidence: float,
) -> RendererSemanticTurn:
    primary_stance = max(
        topic_effects.values(),
        key=lambda value: abs(float(value)),
        default=0.0,
    )
    return RendererSemanticTurn(
        speaker=speaker,
        topics=tuple(topic_effects.keys()),
        stance_band=stance_band(float(primary_stance)),
        argument_band=unit_band(argument_strength, low=0.45, high=0.72, labels=("light", "moderate", "strong")),
        confidence_band=unit_band(confidence, low=0.40, high=0.68, labels=("tentative", "measured", "confident")),
    )


def unit_band(
    value: float,
    *,
    low: float = 0.33,
    high: float = 0.67,
    labels: tuple[str, str, str] = ("low", "moderate", "high"),
) -> str:
    if value < low:
        return labels[0]
    if value < high:
        return labels[1]
    return labels[2]
