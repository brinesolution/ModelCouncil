from __future__ import annotations

from dataclasses import dataclass
import hashlib

import numpy as np

from simulation.domain.agent import ConsumerAgent, clamp01
from simulation.product.knowledge import ProductKnowledge
from simulation.product.taxonomy import ProductTaxonomy


@dataclass(frozen=True, slots=True)
class NeedAssessment:
    value: float
    components: dict[str, float]


def assess_product_need(
    agent: ConsumerAgent,
    product: ProductKnowledge,
    taxonomy: ProductTaxonomy,
    *,
    seed: int,
) -> NeedAssessment:
    if _has_unspecified_life_context(agent):
        return _legacy_need_assessment(agent, product, taxonomy, seed=seed)

    rng = np.random.default_rng(_mixed_seed(seed, agent.agent_id, product.name, taxonomy.form))
    noise = float(rng.normal(0.0, 0.04))
    generic = 0.10 * agent.traits.product_need
    components = _form_components(agent, taxonomy, generic)
    components["idiosyncratic_need"] = noise
    return NeedAssessment(value=clamp01(sum(components.values())), components=components)


def _has_unspecified_life_context(agent: ConsumerAgent) -> bool:
    return (
        agent.context.demographic.key == "unspecified"
        and agent.context.occupation.key == "unspecified"
        and agent.context.decision.key == "unspecified"
        and agent.context.emotion.key == "unspecified"
    )


def _legacy_need_assessment(
    agent: ConsumerAgent,
    product: ProductKnowledge,
    taxonomy: ProductTaxonomy,
    *,
    seed: int,
) -> NeedAssessment:
    rng = np.random.default_rng(
        _legacy_mixed_seed(seed, agent.agent_id, product.name, taxonomy.family)
    )
    affinity = _legacy_category_affinity(agent, taxonomy.family)
    noise = float(rng.normal(0.0, 0.055))
    components = {
        "product_need": 0.48 * agent.traits.product_need,
        "category_affinity": 0.47 * affinity,
        "logicality": 0.05 * agent.traits.logicality,
        "idiosyncratic_need": noise,
    }
    return NeedAssessment(value=clamp01(sum(components.values())), components=components)


def _legacy_category_affinity(agent: ConsumerAgent, family: str) -> float:
    traits = agent.traits
    if family == "software_subscription":
        return clamp01(0.28 + 0.42 * traits.technology_adoption + 0.18 * traits.logicality + 0.12 * traits.product_need)
    if family == "education_productivity":
        return clamp01(0.28 + 0.30 * traits.logicality + 0.20 * traits.technology_adoption + 0.14 * traits.product_need)
    if family == "fitness_wellness":
        return clamp01(0.28 + 0.24 * traits.product_need + 0.18 * traits.risk_tolerance + 0.12 * traits.technology_adoption)
    if family == "security_privacy":
        return clamp01(0.25 + 0.34 * (1.0 - traits.risk_tolerance) + 0.18 * traits.logicality + 0.10 * traits.technology_adoption)
    if family == "personal_care_luxury":
        return clamp01(0.14 + 0.24 * agent.income_score + 0.22 * traits.brand_loyalty + 0.20 * traits.emotionality)
    if family == "smart_home":
        return clamp01(0.20 + 0.36 * traits.technology_adoption + 0.17 * traits.product_need + 0.12 * traits.logicality)
    if family == "consumer_electronics":
        return clamp01(0.20 + 0.28 * traits.technology_adoption + 0.18 * agent.income_score + 0.14 * traits.product_need)
    return clamp01(0.22 + 0.52 * traits.product_need + 0.10 * traits.logicality)


def _legacy_mixed_seed(seed: int, agent_id: int, product_name: str, family: str) -> int:
    digest = hashlib.blake2b(
        f"{seed}:{agent_id}:{product_name}:{family}".encode("utf-8"),
        digest_size=8,
    ).digest()
    return int.from_bytes(digest, "big") % (2**32)


def _form_components(
    agent: ConsumerAgent,
    taxonomy: ProductTaxonomy,
    generic: float,
) -> dict[str, float]:
    form = taxonomy.form
    ctx = agent.context

    if form == "education_software":
        return {
            "base": 0.10,
            "generic_motivation": generic,
            "occupation_context": 0.35 * _occupation_relevance(
                agent,
                {
                    "student": 1.0,
                    "education": 0.90,
                    "software_tech": 0.30,
                    "business_services": 0.25,
                    "government_public": 0.25,
                    "entrepreneur": 0.25,
                    "healthcare": 0.20,
                    "other_worker": 0.20,
                    "retail_operations": 0.10,
                    "skilled_trade": 0.10,
                },
            ),
            "research_tendency": 0.12 * ctx.behaviour.research_tendency,
            "evidence_orientation": 0.10 * ctx.decision.evidence_requirement,
            "digital_comfort": 0.12 * ctx.technology.digital_comfort,
        }

    if form == "software_service":
        return {
            "base": 0.08,
            "generic_motivation": 0.10 * agent.traits.product_need,
            "technology_adoption": 0.28 * agent.traits.technology_adoption,
            "logicality": 0.14 * agent.traits.logicality,
            "digital_comfort": 0.16 * ctx.technology.digital_comfort,
            "convenience_preference": 0.14 * ctx.behaviour.convenience_preference,
        }

    if form == "business_saas":
        return {
            "base": 0.08,
            "generic_motivation": generic,
            "occupation_context": 0.38 * _occupation_relevance(
                agent,
                {
                    "business_services": 1.0,
                    "software_tech": 0.92,
                    "entrepreneur": 0.92,
                    "government_public": 0.50,
                    "other_worker": 0.35,
                    "education": 0.30,
                    "healthcare": 0.25,
                    "retail_operations": 0.25,
                    "skilled_trade": 0.20,
                    "student": 0.05,
                },
            ),
            "time_pressure": 0.14 * ctx.occupation.time_pressure,
            "convenience_preference": 0.14 * ctx.behaviour.convenience_preference,
            "digital_comfort": 0.10 * ctx.technology.digital_comfort,
            "research_tendency": 0.06 * ctx.behaviour.research_tendency,
        }

    if form == "meal_planning_software":
        return {
            "base": 0.08,
            "generic_motivation": generic,
            "household_context": 0.30 * _household_relevance(agent),
            "time_pressure": 0.20 * ctx.occupation.time_pressure,
            "convenience_preference": 0.20 * ctx.behaviour.convenience_preference,
            "value_orientation": 0.08 * ctx.economic.value_orientation,
        }

    if form in {"vpn_service", "security_service", "indoor_security_camera"}:
        household_component = 0.10 * _household_relevance(agent) if form == "indoor_security_camera" else 0.0
        return {
            "base": 0.08,
            "generic_motivation": 0.08 * agent.traits.product_need,
            "security_preference": 0.28 * ctx.emotion.security_preference,
            "privacy_concern": 0.24 * ctx.technology.privacy_concern,
            "research_tendency": 0.10 * ctx.behaviour.research_tendency,
            "technology_exposure": 0.08 * ctx.occupation.tech_exposure,
            "household_context": household_component,
        }

    if form in {"fragrance", "beauty_device", "personal_care"}:
        quality_weight = 0.12 if form == "beauty_device" else 0.05
        return {
            "base": 0.07,
            "generic_motivation": 0.08 * agent.traits.product_need,
            "luxury_preference": 0.27 * ctx.economic.luxury_preference,
            "status_motivation": 0.23 * ctx.emotion.status_motivation,
            "brand_loyalty": 0.15 * agent.traits.brand_loyalty,
            "income": 0.10 * agent.income_score,
            "quality_sensitivity": quality_weight * ctx.behaviour.quality_sensitivity,
        }

    if form == "audio_earbuds":
        return {
            "base": 0.08,
            "generic_motivation": 0.08 * agent.traits.product_need,
            "digital_comfort": 0.24 * ctx.technology.digital_comfort,
            "technology_adoption": 0.19 * agent.traits.technology_adoption,
            "quality_sensitivity": 0.17 * ctx.behaviour.quality_sensitivity,
            "income": 0.12 * agent.income_score,
            "convenience_preference": 0.10 * ctx.behaviour.convenience_preference,
        }

    if form == "portable_power_bank":
        return {
            "base": 0.08,
            "generic_motivation": 0.08 * agent.traits.product_need,
            "technology_exposure": 0.22 * ctx.occupation.tech_exposure,
            "time_pressure": 0.16 * ctx.occupation.time_pressure,
            "digital_comfort": 0.18 * ctx.technology.digital_comfort,
            "quality_sensitivity": 0.16 * ctx.behaviour.quality_sensitivity,
            "convenience_preference": 0.12 * ctx.behaviour.convenience_preference,
        }

    if form == "robot_vacuum":
        return {
            "base": 0.08,
            "generic_motivation": 0.08 * agent.traits.product_need,
            "household_context": 0.25 * _household_relevance(agent),
            "time_pressure": 0.18 * ctx.occupation.time_pressure,
            "convenience_preference": 0.20 * ctx.behaviour.convenience_preference,
            "income": 0.12 * agent.income_score,
            "technology_adoption": 0.10 * agent.traits.technology_adoption,
        }

    if form == "finance_software":
        return {
            "base": 0.08,
            "generic_motivation": 0.08 * agent.traits.product_need,
            "savings_orientation": 0.25 * ctx.economic.savings_orientation,
            "value_orientation": 0.18 * ctx.economic.value_orientation,
            "research_tendency": 0.18 * ctx.behaviour.research_tendency,
            "price_attention": 0.12 * agent.traits.price_sensitivity,
            "digital_comfort": 0.08 * ctx.technology.digital_comfort,
        }

    if form == "fitness_service":
        age_fit = max(0.0, 1.0 - max(0, agent.age - 55) / 30.0)
        return {
            "base": 0.09,
            "generic_motivation": 0.12 * agent.traits.product_need,
            "convenience_preference": 0.18 * ctx.behaviour.convenience_preference,
            "optimism": 0.15 * ctx.emotion.optimism,
            "early_adopter": 0.14 * ctx.technology.early_adopter,
            "technology_adoption": 0.10 * agent.traits.technology_adoption,
            "age_fit": 0.08 * age_fit,
        }

    if form == "smart_home_device":
        return {
            "base": 0.08,
            "generic_motivation": 0.10 * agent.traits.product_need,
            "household_context": 0.22 * _household_relevance(agent),
            "technology_adoption": 0.22 * agent.traits.technology_adoption,
            "convenience_preference": 0.18 * ctx.behaviour.convenience_preference,
            "income": 0.10 * agent.income_score,
        }

    # Unknown forms keep a generic fallback, but generic product_need is no longer
    # enough to make unrelated known categories move together.
    return {
        "base": 0.15,
        "generic_motivation": 0.25 * agent.traits.product_need,
        "logicality": 0.10 * agent.traits.logicality,
        "technology_adoption": 0.10 * agent.traits.technology_adoption,
    }


def _occupation_relevance(agent: ConsumerAgent, weights: dict[str, float]) -> float:
    return weights.get(agent.context.occupation.key, 0.20)


def _household_relevance(agent: ConsumerAgent) -> float:
    household = agent.context.demographic.household_tendency.lower()
    if "children" in household:
        return 1.0
    if "dual-income" in household or "dual income" in household:
        return 0.95
    if "family" in household:
        return 0.85
    if "couple" in household:
        return 0.45
    if "single" in household or "shared" in household:
        return 0.15
    if "independent" in household:
        return 0.30
    return 0.40


def _mixed_seed(seed: int, agent_id: int, product_name: str, form: str) -> int:
    digest = hashlib.blake2b(
        f"{seed}:{agent_id}:{product_name}:{form}".encode("utf-8"),
        digest_size=8,
    ).digest()
    return int.from_bytes(digest, "big") % (2**32)
