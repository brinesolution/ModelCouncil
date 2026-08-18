from __future__ import annotations

from dataclasses import dataclass

from simulation.conversation.models import ConversationPair, ConversationResult
from simulation.domain.agent import ConsumerAgent
from simulation.product.knowledge import ProductKnowledge
from simulation.product.pricing import BillingCadence, ConsumerPriceContext


@dataclass(frozen=True, slots=True)
class AgentLanguageProfile:
    agent_id: int
    age: int
    occupation: str
    primary_language: str
    locale: str
    logicality: float
    emotionality: float
    sociability: float
    stubbornness: float
    influence_power: float
    confidence: float
    knowledge: float
    overall_opinion: float
    income_score: float = 0.5
    price_sensitivity: float = 0.5
    technology_adoption: float = 0.5
    product_need: float = 0.5
    risk_tolerance: float = 0.5
    brand_loyalty: float = 0.5

    @classmethod
    def from_agent(cls, agent: ConsumerAgent) -> "AgentLanguageProfile":
        return cls(
            agent_id=agent.agent_id,
            age=agent.age,
            occupation=agent.occupation,
            income_score=agent.income_score,
            primary_language=agent.primary_language,
            locale=agent.locale,
            sociability=agent.traits.sociability,
            price_sensitivity=agent.traits.price_sensitivity,
            technology_adoption=agent.traits.technology_adoption,
            emotionality=agent.traits.emotionality,
            logicality=agent.traits.logicality,
            stubbornness=agent.traits.stubbornness,
            influence_power=agent.traits.influence_power,
            product_need=agent.traits.product_need,
            risk_tolerance=agent.traits.risk_tolerance,
            brand_loyalty=agent.traits.brand_loyalty,
            confidence=agent.state.confidence,
            knowledge=agent.state.knowledge,
            overall_opinion=agent.state.overall_opinion,
        )


@dataclass(frozen=True, slots=True)
class ProductLanguageContext:
    name: str
    category: str
    price: float | None
    currency: str
    pitch_excerpt: str
    billing_cadence: BillingCadence = BillingCadence.one_time

    @classmethod
    def from_product(
        cls,
        product: ProductKnowledge,
        *,
        max_pitch_chars: int = 1200,
    ) -> "ProductLanguageContext":
        if max_pitch_chars < 1:
            raise ValueError("max_pitch_chars must be at least 1")
        compact_pitch = " ".join(product.pitch.split())[:max_pitch_chars]
        return cls(
            name=product.name,
            category=product.category,
            price=product.price,
            currency=product.currency,
            pitch_excerpt=compact_pitch,
            billing_cadence=product.resolved_billing_cadence,
        )


@dataclass(frozen=True, slots=True)
class ConversationLanguageContext:
    agent_a: AgentLanguageProfile
    agent_b: AgentLanguageProfile
    agent_a_price_context: ConsumerPriceContext | None = None
    agent_b_price_context: ConsumerPriceContext | None = None

    @classmethod
    def from_agents(
        cls,
        agent_a: ConsumerAgent,
        agent_b: ConsumerAgent,
        *,
        agent_a_price_context: ConsumerPriceContext | None = None,
        agent_b_price_context: ConsumerPriceContext | None = None,
    ) -> "ConversationLanguageContext":
        return cls(
            agent_a=AgentLanguageProfile.from_agent(agent_a),
            agent_b=AgentLanguageProfile.from_agent(agent_b),
            agent_a_price_context=(
                agent_a_price_context.with_stance(agent_a.state.beliefs.price)
                if agent_a_price_context is not None
                else None
            ),
            agent_b_price_context=(
                agent_b_price_context.with_stance(agent_b.state.beliefs.price)
                if agent_b_price_context is not None
                else None
            ),
        )


@dataclass(frozen=True, slots=True)
class ConversationLedgerEntry:
    round_index: int
    pair: ConversationPair
    result: ConversationResult
    language_context: ConversationLanguageContext
    trust: float
    relationship_strength: float
    similarity: float
    weak_tie: bool
    importance: float = 0.0
    llm_selected: bool = False

    @property
    def conversation_id(self) -> str:
        return self.pair.conversation_id

    @property
    def agent_a_id(self) -> int:
        return self.pair.agent_a_id

    @property
    def agent_b_id(self) -> int:
        return self.pair.agent_b_id
