from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from simulation.domain.agent import ConsumerAgent
from simulation.product.knowledge import ProductKnowledge
from simulation.product.need_model import assess_product_need
from simulation.product.pricing import ConsumerPriceContext, build_consumer_price_context
from simulation.product.semantic_profile import ProductSemanticProfile
from simulation.product.taxonomy import resolve_product_taxonomy
from simulation.audit.logger import RunAuditSink


@dataclass(frozen=True, slots=True)
class ConsumerProductFit:
    need: float
    affordability: float
    adoption_fit: float
    risk_fit: float
    privacy_concern: float
    price_pressure: float
    price_context: ConsumerPriceContext | None = None


def consumer_product_fit(
    agent: ConsumerAgent,
    product: ProductKnowledge,
    profile: ProductSemanticProfile,
    *,
    seed: int,
    audit: RunAuditSink | None = None,
) -> ConsumerProductFit:
    taxonomy = resolve_product_taxonomy(
        product.category,
        " ".join((product.pitch, *product.features)),
    )
    need_assessment = assess_product_need(agent, product, taxonomy, seed=seed)
    need = need_assessment.value
    idiosyncratic_need = need_assessment.components.get("idiosyncratic_need", 0.0)

    complexity_penalty = profile.complexity * (1.0 - 0.65 * agent.traits.technology_adoption)
    adoption_fit = _clip01(
        0.62 * agent.traits.technology_adoption
        + 0.18 * agent.traits.logicality
        + 0.20 * agent.traits.risk_tolerance
        - 0.38 * complexity_penalty
    )

    privacy_concern = _clip01(
        0.58 * (1.0 - agent.traits.risk_tolerance)
        + 0.22 * agent.traits.logicality
        + 0.12 * (1.0 - agent.traits.technology_adoption)
        + 0.08 * agent.traits.stubbornness
    )
    profile_risk_components = {
        "reliability_risk": 0.30 * profile.reliability_risk,
        "serviceability_risk": 0.20 * profile.serviceability_risk,
        "safety_risk": 0.30 * profile.safety_risk,
        "data_practice_risk": 0.15 * profile.data_practice_risk,
        "cancellation_friction": 0.05 * profile.cancellation_friction,
    }
    profile_risk = _clip01(sum(profile_risk_components.values()))
    risk_penalty = 0.35 * profile_risk * (1.0 - 0.50 * agent.traits.risk_tolerance)
    risk_fit_components = {
        "risk_tolerance": 0.62 * agent.traits.risk_tolerance,
        "claim_certainty": 0.23 * (1.0 - profile.claim_uncertainty),
        "privacy_fit": 0.15 * (1.0 - profile.privacy_exposure * privacy_concern),
        "profile_risk_penalty": -risk_penalty,
    }
    risk_fit = _clip01(sum(risk_fit_components.values()))

    price_context = build_consumer_price_context(
        agent,
        product,
        category_family=profile.category_family,
        need=need,
        audit=audit,
    )

    fit = ConsumerProductFit(
        need=need,
        affordability=price_context.affordability,
        adoption_fit=adoption_fit,
        risk_fit=risk_fit,
        privacy_concern=privacy_concern,
        price_pressure=price_context.price_pressure,
        price_context=price_context,
    )
    if audit is not None:
        audit.emit(
            "consumer.fit",
            {
                "formula_version": "consumer-fit-v2h",
                "agent_id": agent.agent_id,
                "product_name": product.name,
                "category_family": profile.category_family,
                "product_form": taxonomy.form,
                "inputs": {
                    "product_need": agent.traits.product_need,
                    "technology_adoption": agent.traits.technology_adoption,
                    "logicality": agent.traits.logicality,
                    "risk_tolerance": agent.traits.risk_tolerance,
                    "stubbornness": agent.traits.stubbornness,
                    "income_score": agent.income_score,
                    "price_sensitivity": agent.traits.price_sensitivity,
                    "complexity": profile.complexity,
                    "claim_uncertainty": profile.claim_uncertainty,
                    "privacy_exposure": profile.privacy_exposure,
                    "reliability_risk": profile.reliability_risk,
                    "serviceability_risk": profile.serviceability_risk,
                    "safety_risk": profile.safety_risk,
                    "data_practice_risk": profile.data_practice_risk,
                    "cancellation_friction": profile.cancellation_friction,
                },
                "components": {
                    "need_components": need_assessment.components,
                    "idiosyncratic_need": idiosyncratic_need,
                    "complexity_penalty": complexity_penalty,
                    "profile_risk": profile_risk,
                    "profile_risk_components": profile_risk_components,
                },
                "formula_components": {
                    "need": need_assessment.components,
                    "adoption_fit": {
                        "technology_adoption": 0.62 * agent.traits.technology_adoption,
                        "logicality": 0.18 * agent.traits.logicality,
                        "risk_tolerance": 0.20 * agent.traits.risk_tolerance,
                        "complexity_penalty": -0.38 * complexity_penalty,
                    },
                    "privacy_concern": {
                        "risk_aversion": 0.58 * (1.0 - agent.traits.risk_tolerance),
                        "logicality": 0.22 * agent.traits.logicality,
                        "technology_skepticism": 0.12 * (1.0 - agent.traits.technology_adoption),
                        "stubbornness": 0.08 * agent.traits.stubbornness,
                    },
                    "risk_fit": risk_fit_components,
                },
                "result": fit,
            },
            agent_ids=[agent.agent_id],
        )
    return fit


def _clip01(value: float) -> float:
    return float(np.clip(value, 0.0, 1.0))
