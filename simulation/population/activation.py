from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


ActivationStatus = Literal["active", "derived", "provenance_only"]


@dataclass(frozen=True, slots=True)
class TraitActivation:
    category: str
    column: str
    status: ActivationStatus
    consumer_path: str | None


# This manifest is intentionally explicit. Loading a workbook column does not
# imply that it influences the simulation; every column must declare its role.
_MANIFEST: dict[str, dict[str, tuple[ActivationStatus, str | None]]] = {
    "archetypes": {
        "preferred_decision": ("active", "population.soft_prior.decision"),
        "preferred_economic": ("active", "population.soft_prior.economic"),
        "preferred_personality": ("active", "population.soft_prior.personality"),
        "preferred_social": ("active", "population.soft_prior.social"),
        "preferred_technology": ("active", "population.soft_prior.technology"),
        "description": ("provenance_only", None),
    },
    "compatibility_rules": {
        "condition": ("active", "population.compatibility.condition"),
        "effect": ("active", "population.compatibility.effect"),
        "magnitude": ("active", "population.compatibility.magnitude"),
        "target": ("active", "population.compatibility.target"),
        "reason": ("provenance_only", None),
    },
    "consumer_behaviour": {
        "brand_loyalty": ("active", "traits.brand_loyalty"),
        "switching_tendency": ("active", "context.behaviour.switching_tendency"),
        "research_tendency": ("active", "context.behaviour.research_tendency"),
        "quality_sensitivity": ("active", "context.behaviour.quality_sensitivity"),
        "convenience_preference": ("active", "context.behaviour.convenience_preference"),
        "review_trust": ("active", "context.behaviour.review_trust"),
        "purchase_frequency": ("active", "context.behaviour.purchase_frequency"),
        "description": ("provenance_only", None),
    },
    "decision_styles": {
        "logic_weight": ("active", "context.decision.logic_weight"),
        "emotion_weight": ("active", "context.decision.emotion_weight"),
        "social_weight": ("active", "context.decision.social_weight"),
        "price_weight": ("active", "context.decision.price_weight"),
        "decision_speed": ("active", "context.decision.decision_speed"),
        "evidence_requirement": ("active", "context.decision.evidence_requirement"),
        "description": ("provenance_only", None),
    },
    "demographics": {
        "age_min": ("derived", "agent.age"),
        "age_max": ("derived", "agent.age"),
        "urbanity": ("active", "context.demographic.urbanity"),
        "household_tendency": ("active", "context.demographic.household_tendency"),
        "description": ("provenance_only", None),
    },
    "economic_traits": {
        "price_sensitivity": ("active", "traits.price_sensitivity"),
        "discount_sensitivity": ("active", "context.economic.discount_sensitivity"),
        "savings_orientation": ("active", "context.economic.savings_orientation"),
        "luxury_preference": ("active", "context.economic.luxury_preference"),
        "value_orientation": ("active", "context.economic.value_orientation"),
        "spending_tendency": ("active", "context.economic.spending_tendency"),
        "description": ("provenance_only", None),
    },
    "emotions": {
        "optimism": ("active", "context.emotion.optimism"),
        "fear_sensitivity": ("active", "context.emotion.fear_sensitivity"),
        "excitement_sensitivity": ("active", "context.emotion.excitement_sensitivity"),
        "fomo": ("active", "context.emotion.fomo"),
        "status_motivation": ("active", "context.emotion.status_motivation"),
        "security_preference": ("active", "context.emotion.security_preference"),
        "reactance": ("active", "context.emotion.reactance"),
        "description": ("provenance_only", None),
    },
    "occupations": {
        "min_age": ("derived", "agent.age"),
        "income_min": ("derived", "agent.income_score"),
        "income_max": ("derived", "agent.income_score"),
        "tech_exposure": ("active", "context.occupation.tech_exposure"),
        "time_pressure": ("active", "context.occupation.time_pressure"),
        "description": ("provenance_only", None),
    },
    "personality": {
        "logicality": ("active", "traits.logicality"),
        "emotionality": ("active", "traits.emotionality"),
        "stubbornness": ("active", "traits.stubbornness"),
        "risk_tolerance": ("active", "traits.risk_tolerance"),
        "sociability": ("active", "traits.sociability"),
        "curiosity": ("provenance_only", None),
        "description": ("provenance_only", None),
    },
    "social_behaviour": {
        "sociability": ("active", "traits.sociability"),
        "peer_influence": ("active", "context.social.peer_influence"),
        "family_influence": ("active", "context.social.family_influence"),
        "social_proof": ("active", "context.social.social_proof"),
        "influencer_susceptibility": ("active", "context.social.influencer_susceptibility"),
        "persuasion_power": ("derived", "traits.influence_power"),
        "message_accuracy": ("active", "context.social.message_accuracy"),
        "description": ("provenance_only", None),
    },
    "technology": {
        "technology_adoption": ("active", "traits.technology_adoption"),
        "ai_familiarity": ("active", "context.technology.ai_familiarity"),
        "ai_trust": ("active", "context.technology.ai_trust"),
        "privacy_concern": ("active", "context.technology.privacy_concern"),
        "digital_comfort": ("active", "context.technology.digital_comfort"),
        "early_adopter": ("active", "context.technology.early_adopter"),
        "description": ("provenance_only", None),
    },
}


def trait_activation_manifest() -> tuple[TraitActivation, ...]:
    return tuple(
        TraitActivation(category, column, status, path)
        for category, columns in sorted(_MANIFEST.items())
        for column, (status, path) in sorted(columns.items())
    )


def activation_for(category: str, column: str) -> TraitActivation | None:
    item = _MANIFEST.get(category, {}).get(column)
    if item is None:
        return None
    status, path = item
    return TraitActivation(category, column, status, path)
