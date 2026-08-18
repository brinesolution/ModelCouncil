from dataclasses import dataclass, field

from simulation.domain.consumer_context import ConsumerContext


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def clamp_opinion(value: float) -> float:
    return max(-1.0, min(1.0, value))


@dataclass(slots=True)
class AgentTraits:
    sociability: float
    price_sensitivity: float
    technology_adoption: float
    emotionality: float
    logicality: float
    stubbornness: float
    influence_power: float
    product_need: float
    risk_tolerance: float
    brand_loyalty: float

    def normalized(self) -> "AgentTraits":
        return AgentTraits(**{name: clamp01(value) for name, value in self.as_dict().items()})

    def as_dict(self) -> dict[str, float]:
        return {
            "sociability": self.sociability,
            "price_sensitivity": self.price_sensitivity,
            "technology_adoption": self.technology_adoption,
            "emotionality": self.emotionality,
            "logicality": self.logicality,
            "stubbornness": self.stubbornness,
            "influence_power": self.influence_power,
            "product_need": self.product_need,
            "risk_tolerance": self.risk_tolerance,
            "brand_loyalty": self.brand_loyalty,
        }


@dataclass(slots=True)
class ProductBeliefs:
    price: float = 0.0
    usefulness: float = 0.0
    quality: float = 0.0
    trust: float = 0.0
    novelty: float = 0.0
    privacy: float = 0.0

    def as_dict(self) -> dict[str, float]:
        return {
            "price": self.price,
            "usefulness": self.usefulness,
            "quality": self.quality,
            "trust": self.trust,
            "novelty": self.novelty,
            "privacy": self.privacy,
        }

    def apply(self, updates: dict[str, float]) -> None:
        for topic, value in updates.items():
            if hasattr(self, topic):
                setattr(self, topic, clamp_opinion(value))


@dataclass(slots=True)
class AgentState:
    beliefs: ProductBeliefs = field(default_factory=ProductBeliefs)
    overall_opinion: float = 0.0
    confidence: float = 0.5
    knowledge: float = 0.0
    purchase_intent: float = 0.0
    product_salience: float = 0.0

    def normalize(self) -> None:
        self.overall_opinion = clamp_opinion(self.overall_opinion)
        self.confidence = clamp01(self.confidence)
        self.knowledge = clamp01(self.knowledge)
        self.purchase_intent = clamp01(self.purchase_intent)
        self.product_salience = clamp01(self.product_salience)


@dataclass(slots=True)
class ConsumerAgent:
    agent_id: int
    age: int
    occupation: str
    income_score: float
    traits: AgentTraits
    state: AgentState = field(default_factory=AgentState)
    context: ConsumerContext = field(default_factory=ConsumerContext)
    primary_language: str = "English"
    locale: str = "Indian English"
