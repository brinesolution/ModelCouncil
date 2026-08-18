from __future__ import annotations

from dataclasses import dataclass, field, replace


def _clip01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


@dataclass(slots=True)
class DemographicContext:
    key: str = "unspecified"
    urbanity: float = 0.5
    household_tendency: str = "unspecified"

    def normalized(self) -> "DemographicContext":
        return replace(self, urbanity=_clip01(self.urbanity))


@dataclass(slots=True)
class OccupationContext:
    key: str = "unspecified"
    tech_exposure: float = 0.5
    time_pressure: float = 0.5

    def normalized(self) -> "OccupationContext":
        return OccupationContext(
            key=self.key,
            tech_exposure=_clip01(self.tech_exposure),
            time_pressure=_clip01(self.time_pressure),
        )


@dataclass(slots=True)
class EconomicContext:
    discount_sensitivity: float = 0.5
    savings_orientation: float = 0.5
    luxury_preference: float = 0.5
    value_orientation: float = 0.5
    spending_tendency: float = 0.5

    def normalized(self) -> "EconomicContext":
        return EconomicContext(
            discount_sensitivity=_clip01(self.discount_sensitivity),
            savings_orientation=_clip01(self.savings_orientation),
            luxury_preference=_clip01(self.luxury_preference),
            value_orientation=_clip01(self.value_orientation),
            spending_tendency=_clip01(self.spending_tendency),
        )


@dataclass(slots=True)
class DecisionContext:
    key: str = "unspecified"
    logic_weight: float = 0.5
    emotion_weight: float = 0.5
    social_weight: float = 0.5
    price_weight: float = 0.5
    decision_speed: float = 0.5
    evidence_requirement: float = 0.5

    def normalized(self) -> "DecisionContext":
        return DecisionContext(
            key=self.key,
            logic_weight=_clip01(self.logic_weight),
            emotion_weight=_clip01(self.emotion_weight),
            social_weight=_clip01(self.social_weight),
            price_weight=_clip01(self.price_weight),
            decision_speed=_clip01(self.decision_speed),
            evidence_requirement=_clip01(self.evidence_requirement),
        )


@dataclass(slots=True)
class EmotionContext:
    key: str = "unspecified"
    optimism: float = 0.5
    fear_sensitivity: float = 0.5
    excitement_sensitivity: float = 0.5
    fomo: float = 0.5
    status_motivation: float = 0.5
    security_preference: float = 0.5
    reactance: float = 0.5

    def normalized(self) -> "EmotionContext":
        return EmotionContext(
            key=self.key,
            optimism=_clip01(self.optimism),
            fear_sensitivity=_clip01(self.fear_sensitivity),
            excitement_sensitivity=_clip01(self.excitement_sensitivity),
            fomo=_clip01(self.fomo),
            status_motivation=_clip01(self.status_motivation),
            security_preference=_clip01(self.security_preference),
            reactance=_clip01(self.reactance),
        )


@dataclass(slots=True)
class BehaviourContext:
    switching_tendency: float = 0.5
    research_tendency: float = 0.5
    quality_sensitivity: float = 0.5
    convenience_preference: float = 0.5
    review_trust: float = 0.5
    purchase_frequency: float = 0.5

    def normalized(self) -> "BehaviourContext":
        return BehaviourContext(
            switching_tendency=_clip01(self.switching_tendency),
            research_tendency=_clip01(self.research_tendency),
            quality_sensitivity=_clip01(self.quality_sensitivity),
            convenience_preference=_clip01(self.convenience_preference),
            review_trust=_clip01(self.review_trust),
            purchase_frequency=_clip01(self.purchase_frequency),
        )


@dataclass(slots=True)
class TechnologyContext:
    ai_familiarity: float = 0.5
    ai_trust: float = 0.5
    privacy_concern: float = 0.5
    digital_comfort: float = 0.5
    early_adopter: float = 0.5

    def normalized(self) -> "TechnologyContext":
        return TechnologyContext(
            ai_familiarity=_clip01(self.ai_familiarity),
            ai_trust=_clip01(self.ai_trust),
            privacy_concern=_clip01(self.privacy_concern),
            digital_comfort=_clip01(self.digital_comfort),
            early_adopter=_clip01(self.early_adopter),
        )


@dataclass(slots=True)
class SocialContext:
    peer_influence: float = 0.5
    family_influence: float = 0.5
    social_proof: float = 0.5
    influencer_susceptibility: float = 0.5
    social_susceptibility: float = 0.5
    message_accuracy: float = 0.8

    def normalized(self) -> "SocialContext":
        return SocialContext(
            peer_influence=_clip01(self.peer_influence),
            family_influence=_clip01(self.family_influence),
            social_proof=_clip01(self.social_proof),
            influencer_susceptibility=_clip01(self.influencer_susceptibility),
            social_susceptibility=_clip01(self.social_susceptibility),
            message_accuracy=_clip01(self.message_accuracy),
        )


@dataclass(slots=True)
class ConsumerContext:
    demographic: DemographicContext = field(default_factory=DemographicContext)
    occupation: OccupationContext = field(default_factory=OccupationContext)
    economic: EconomicContext = field(default_factory=EconomicContext)
    decision: DecisionContext = field(default_factory=DecisionContext)
    emotion: EmotionContext = field(default_factory=EmotionContext)
    behaviour: BehaviourContext = field(default_factory=BehaviourContext)
    technology: TechnologyContext = field(default_factory=TechnologyContext)
    social: SocialContext = field(default_factory=SocialContext)
    archetype_key: str = "unspecified"

    def normalized(self) -> "ConsumerContext":
        return ConsumerContext(
            demographic=self.demographic.normalized(),
            occupation=self.occupation.normalized(),
            economic=self.economic.normalized(),
            decision=self.decision.normalized(),
            emotion=self.emotion.normalized(),
            behaviour=self.behaviour.normalized(),
            technology=self.technology.normalized(),
            social=self.social.normalized(),
            archetype_key=self.archetype_key,
        )
