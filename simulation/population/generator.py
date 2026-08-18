from __future__ import annotations

import inspect
import numpy as np

from simulation.domain.agent import AgentState, AgentTraits, ConsumerAgent
from simulation.domain.consumer_context import (
    BehaviourContext,
    ConsumerContext,
    DecisionContext,
    DemographicContext,
    EconomicContext,
    EmotionContext,
    OccupationContext,
    SocialContext,
    TechnologyContext,
)
from simulation.population.compatibility import apply_compatibility_rules, parse_compatibility_rule
from simulation.population.correlations import (
    clip01,
    correlated_influence_power,
    correlated_logicality,
    correlated_price_sensitivity,
    correlated_risk_tolerance,
    jitter_normalized,
    sample_income,
)
from simulation.population.sampling import (
    sample_occupation_for_demographic,
    sample_weighted,
    sample_with_soft_preference,
)
from simulation.population.trait_repository import TraitCatalog, TraitRepository, TraitValue
from simulation.audit.logger import RunAuditSink

OCCUPATIONS = (
    "Student",
    "Software Professional",
    "Business Professional",
    "Healthcare Professional",
    "Educator",
    "Creative Professional",
    "Self Employed",
    "Other",
)


def generate_population(
    size: int,
    seed: int = 42,
    traits: TraitRepository | None = None,
    audit: RunAuditSink | None = None,
) -> list[ConsumerAgent]:
    """Generate a reproducible synthetic population.

    When an explicit trait repository is supplied its normalized categories become
    the population priors. Without one, the original bootstrap distributions remain
    available so tests and development never depend on external workbook files.
    """
    if size < 2:
        raise ValueError("Population size must be at least 2.")

    rng = np.random.default_rng(seed)
    if traits is None:
        return _generate_bootstrap_population(size=size, rng=rng, audit=audit)
    load_catalog = traits.load_catalog
    if audit is not None and "audit" in inspect.signature(load_catalog).parameters:
        catalog = load_catalog(audit=audit)
    else:
        catalog = load_catalog()
    return _generate_catalog_population(size=size, rng=rng, catalog=catalog, audit=audit)


def _generate_catalog_population(
    size: int,
    rng: np.random.Generator,
    catalog: TraitCatalog,
    audit: RunAuditSink | None = None,
) -> list[ConsumerAgent]:
    agents: list[ConsumerAgent] = []
    compatibility_rules = (
        tuple(parse_compatibility_rule(value) for value in catalog.category("compatibility_rules"))
        if catalog.has_category("compatibility_rules")
        else ()
    )

    for agent_id in range(size):
        demographic = _sample(catalog, "demographics", rng) if catalog.has_category("demographics") else None
        occupation = (
            sample_occupation_for_demographic(catalog.category("occupations"), demographic, rng)
            if demographic is not None
            else _sample(catalog, "occupations", rng)
        )
        archetype = _sample(catalog, "archetypes", rng) if catalog.has_category("archetypes") else None
        personality = _sample_with_archetype_preference(
            catalog, "personality", rng, archetype, "preferred_personality"
        )
        economic = _sample_with_archetype_preference(
            catalog, "economic_traits", rng, archetype, "preferred_economic"
        )
        social = _sample_with_archetype_preference(
            catalog, "social_behaviour", rng, archetype, "preferred_social"
        )
        technology = _sample_with_archetype_preference(
            catalog, "technology", rng, archetype, "preferred_technology"
        )
        behaviour = _sample(catalog, "consumer_behaviour", rng)
        decision = (
            _sample_with_archetype_preference(
                catalog, "decision_styles", rng, archetype, "preferred_decision"
            )
            if catalog.has_category("decision_styles")
            else None
        )
        emotion = _sample(catalog, "emotions", rng) if catalog.has_category("emotions") else None

        occupation_min_age = int(_number(occupation, "min_age", 18))
        if demographic is not None:
            demographic_min_age = int(_number(demographic, "age_min", 18))
            demographic_max_age = int(_number(demographic, "age_max", 55))
            min_age = max(occupation_min_age, demographic_min_age)
            max_age = demographic_max_age
            if min_age > max_age:
                raise ValueError(
                    f"Occupation {occupation.key!r} is incompatible with demographic {demographic.key!r}."
                )
        else:
            demographic_min_age = 18
            demographic_max_age = max(occupation_min_age + 1, 55)
            min_age = occupation_min_age
            max_age = demographic_max_age
        age = int(rng.integers(min_age, max_age + 1))

        income_trace: dict[str, object] = {}
        income_score = sample_income(
            rng,
            _number(occupation, "income_min", 0.15),
            _number(occupation, "income_max", 0.75),
            occupation.key,
            trace=income_trace,
        )

        emotionality_trace: dict[str, float] = {}
        emotionality = jitter_normalized(
            rng,
            _number(personality, "emotionality", 0.5),
            sigma=0.06,
            trace=emotionality_trace,
        )
        base_logicality = _number(personality, "logicality", 0.55)
        logicality_trace: dict[str, float] = {}
        logicality = correlated_logicality(
            rng,
            base_logicality,
            emotionality,
            decision_logic_weight=(
                _number(decision, "logic_weight", 0.5) if decision is not None else 0.5
            ),
            trace=logicality_trace,
        )
        stubbornness_trace: dict[str, float] = {}
        stubbornness = jitter_normalized(
            rng,
            _number(personality, "stubbornness", 0.5),
            sigma=0.06,
            trace=stubbornness_trace,
        )
        risk_tolerance_trace: dict[str, float] = {}
        risk_tolerance = correlated_risk_tolerance(
            rng,
            _number(personality, "risk_tolerance", 0.5),
            decision_speed=(
                _number(decision, "decision_speed", 0.5) if decision is not None else 0.5
            ),
            fear_sensitivity=(
                _number(emotion, "fear_sensitivity", 0.5) if emotion is not None else 0.5
            ),
            trace=risk_tolerance_trace,
        )

        personality_social = _number(personality, "sociability", 0.5)
        social_profile = _number(social, "sociability", personality_social)
        sociability_center = 0.35 * personality_social + 0.65 * social_profile
        sociability_trace: dict[str, float] = {}
        sociability = jitter_normalized(
            rng,
            sociability_center,
            sigma=0.06,
            trace=sociability_trace,
        )
        sociability_trace.update(
            {
                "personality_social": personality_social,
                "personality_component": 0.35 * personality_social,
                "social_profile": social_profile,
                "social_component": 0.65 * social_profile,
            }
        )

        price_sensitivity_trace: dict[str, float] = {}
        price_sensitivity = correlated_price_sensitivity(
            rng,
            _number(economic, "price_sensitivity", 0.55),
            income_score,
            trace=price_sensitivity_trace,
        )
        technology_adoption_trace: dict[str, float] = {}
        technology_adoption = jitter_normalized(
            rng,
            _number(technology, "technology_adoption", 0.55),
            sigma=0.06,
            trace=technology_adoption_trace,
        )
        influence_power_trace: dict[str, float] = {}
        influence_power = correlated_influence_power(
            rng,
            sociability=sociability,
            base_persuasion=_number(social, "persuasion_power", 0.45),
            decision_social_weight=(
                _number(decision, "social_weight", 0.5) if decision is not None else 0.5
            ),
            message_accuracy=_number(social, "message_accuracy", 0.8),
            trace=influence_power_trace,
        )
        brand_loyalty_trace: dict[str, float] = {}
        brand_loyalty = jitter_normalized(
            rng,
            _number(behaviour, "brand_loyalty", 0.45),
            sigma=0.07,
            trace=brand_loyalty_trace,
        )
        product_need_raw = float(rng.beta(2.0, 2.0))
        product_need = clip01(product_need_raw)

        confidence_raw = float(rng.normal(0.52, 0.14))
        salience_raw = float(rng.normal(0.65, 0.10))
        state = AgentState(
            confidence=clip01(confidence_raw),
            knowledge=0.0,
            product_salience=clip01(salience_raw),
        )
        agent = ConsumerAgent(
            agent_id=agent_id,
            age=age,
            occupation=occupation.label,
            income_score=income_score,
            traits=AgentTraits(
                sociability=sociability,
                price_sensitivity=price_sensitivity,
                technology_adoption=technology_adoption,
                emotionality=emotionality,
                logicality=logicality,
                stubbornness=stubbornness,
                influence_power=influence_power,
                product_need=product_need,
                risk_tolerance=risk_tolerance,
                brand_loyalty=brand_loyalty,
            ),
            state=state,
            context=ConsumerContext(
                demographic=_demographic_context_from(demographic),
                occupation=_occupation_context_from(occupation),
                economic=_economic_context_from(economic),
                decision=_decision_context_from(decision),
                emotion=_emotion_context_from(emotion),
                behaviour=_behaviour_context_from(behaviour),
                technology=_technology_context_from(technology),
                social=_social_context_from(social),
                archetype_key=archetype.key if archetype is not None else "unspecified",
            ).normalized(),
        )
        applied_rules = apply_compatibility_rules(
            agent,
            compatibility_rules,
            condition_values={"occupation": occupation.key},
        )
        if audit is not None:
            for applied in applied_rules:
                audit.emit(
                    "population.compatibility_rule_applied",
                    {
                        "rule_key": applied.rule_key,
                        "target": applied.target,
                        "before": applied.before,
                        "effect": applied.effect,
                        "magnitude": applied.magnitude,
                        "after": applied.after,
                    },
                    agent_ids=[agent_id],
                )

        agents.append(agent)
        if audit is not None:
            audit.emit(
                "population.agent_generated",
                {
                    "source": "excel",
                    "applied_compatibility_rules": applied_rules,
                    "sampled_sources": {
                        **({"demographic": _trait_source_card(demographic)} if demographic is not None else {}),
                        **({"archetype": _trait_source_card(archetype)} if archetype is not None else {}),
                        "occupation": _trait_source_card(occupation),
                        "personality": _trait_source_card(personality),
                        "economic": _trait_source_card(economic),
                        "social": _trait_source_card(social),
                        "technology": _trait_source_card(technology),
                        "consumer_behaviour": _trait_source_card(behaviour),
                        **({"decision_style": _trait_source_card(decision)} if decision is not None else {}),
                        **({"emotion": _trait_source_card(emotion)} if emotion is not None else {}),
                    },
                    "generation_inputs": {
                        "occupation_min_age": occupation_min_age,
                        "demographic_age_min": demographic_min_age,
                        "demographic_age_max": demographic_max_age,
                        "effective_age_min": min_age,
                        "effective_age_max": max_age,
                        "min_age": min_age,
                        "max_age": max_age,
                        "sampled_age": age,
                        "income_min": _number(occupation, "income_min", 0.15),
                        "income_max": _number(occupation, "income_max", 0.75),
                    },
                    "correlation_trace": {
                        "income": income_trace,
                        "emotionality": emotionality_trace,
                        "logicality": logicality_trace,
                        "stubbornness": stubbornness_trace,
                        "risk_tolerance": risk_tolerance_trace,
                        "sociability": sociability_trace,
                        "price_sensitivity": price_sensitivity_trace,
                        "technology_adoption": technology_adoption_trace,
                        "influence_power": influence_power_trace,
                        "brand_loyalty": brand_loyalty_trace,
                        "product_need": {
                            "distribution": "beta(2.0,2.0)",
                            "raw_value": product_need_raw,
                            "result": product_need,
                        },
                        "initial_confidence": {
                            "distribution": "normal(0.52,0.14)",
                            "raw_value": confidence_raw,
                            "result": state.confidence,
                        },
                        "initial_product_salience": {
                            "distribution": "normal(0.65,0.10)",
                            "raw_value": salience_raw,
                            "result": state.product_salience,
                        },
                    },
                    "agent": agent,
                },
                agent_ids=[agent_id],
            )

    return agents


def _demographic_context_from(value: TraitValue | None) -> DemographicContext:
    if value is None:
        return DemographicContext()
    return DemographicContext(
        key=value.key,
        urbanity=_number(value, "urbanity", 0.5),
        household_tendency=_string(value, "household_tendency", "unspecified"),
    )


def _occupation_context_from(value: TraitValue) -> OccupationContext:
    return OccupationContext(
        key=value.key,
        tech_exposure=_number(value, "tech_exposure", 0.5),
        time_pressure=_number(value, "time_pressure", 0.5),
    )


def _economic_context_from(value: TraitValue) -> EconomicContext:
    return EconomicContext(
        discount_sensitivity=_number(value, "discount_sensitivity", 0.5),
        savings_orientation=_number(value, "savings_orientation", 0.5),
        luxury_preference=_number(value, "luxury_preference", 0.5),
        value_orientation=_number(value, "value_orientation", 0.5),
        spending_tendency=_number(value, "spending_tendency", 0.5),
    )


def _decision_context_from(value: TraitValue | None) -> DecisionContext:
    if value is None:
        return DecisionContext()
    return DecisionContext(
        key=value.key,
        logic_weight=_number(value, "logic_weight", 0.5),
        emotion_weight=_number(value, "emotion_weight", 0.5),
        social_weight=_number(value, "social_weight", 0.5),
        price_weight=_number(value, "price_weight", 0.5),
        decision_speed=_number(value, "decision_speed", 0.5),
        evidence_requirement=_number(value, "evidence_requirement", 0.5),
    )


def _emotion_context_from(value: TraitValue | None) -> EmotionContext:
    if value is None:
        return EmotionContext()
    return EmotionContext(
        key=value.key,
        optimism=_number(value, "optimism", 0.5),
        fear_sensitivity=_number(value, "fear_sensitivity", 0.5),
        excitement_sensitivity=_number(value, "excitement_sensitivity", 0.5),
        fomo=_number(value, "fomo", 0.5),
        status_motivation=_number(value, "status_motivation", 0.5),
        security_preference=_number(value, "security_preference", 0.5),
        reactance=_number(value, "reactance", 0.5),
    )


def _behaviour_context_from(value: TraitValue) -> BehaviourContext:
    return BehaviourContext(
        switching_tendency=_number(value, "switching_tendency", 0.5),
        research_tendency=_number(value, "research_tendency", 0.5),
        quality_sensitivity=_number(value, "quality_sensitivity", 0.5),
        convenience_preference=_number(value, "convenience_preference", 0.5),
        review_trust=_number(value, "review_trust", 0.5),
        purchase_frequency=_number(value, "purchase_frequency", 0.5),
    )


def _technology_context_from(value: TraitValue) -> TechnologyContext:
    return TechnologyContext(
        ai_familiarity=_number(value, "ai_familiarity", 0.5),
        ai_trust=_number(value, "ai_trust", 0.5),
        privacy_concern=_number(value, "privacy_concern", 0.5),
        digital_comfort=_number(value, "digital_comfort", 0.5),
        early_adopter=_number(value, "early_adopter", 0.5),
    )


def _social_context_from(value: TraitValue) -> SocialContext:
    peer_influence = _number(value, "peer_influence", 0.5)
    influencer_susceptibility = _number(value, "influencer_susceptibility", 0.5)
    return SocialContext(
        peer_influence=peer_influence,
        family_influence=_number(value, "family_influence", 0.5),
        social_proof=_number(value, "social_proof", 0.5),
        influencer_susceptibility=influencer_susceptibility,
        social_susceptibility=clip01(0.55 * peer_influence + 0.45 * influencer_susceptibility),
        message_accuracy=_number(value, "message_accuracy", 0.8),
    )


def _sample_with_archetype_preference(
    catalog: TraitCatalog,
    category: str,
    rng: np.random.Generator,
    archetype: TraitValue | None,
    preference_attribute: str,
) -> TraitValue:
    preferred_key = (
        _string(archetype, preference_attribute, "") if archetype is not None else ""
    )
    return sample_with_soft_preference(
        catalog.category(category),
        rng,
        preferred_key=preferred_key or None,
        preference_multiplier=2.0,
    )


def _trait_source_card(value: TraitValue) -> dict[str, object]:
    return {
        "key": value.key,
        "label": value.label,
        "probability": value.probability,
        "attributes": dict(value.attributes),
    }


def _sample(catalog: TraitCatalog, category: str, rng: np.random.Generator) -> TraitValue:
    return sample_weighted(catalog.category(category), rng)


def _number(value: TraitValue, attribute: str, default: float) -> float:
    raw = value.attributes.get(attribute, default)
    try:
        return float(raw)
    except (TypeError, ValueError):
        return default


def _string(value: TraitValue, attribute: str, default: str) -> str:
    raw = value.attributes.get(attribute, default)
    if raw is None:
        return default
    text = str(raw).strip()
    return text if text else default


def _generate_bootstrap_population(
    size: int,
    rng: np.random.Generator,
    audit: RunAuditSink | None = None,
) -> list[ConsumerAgent]:
    agents: list[ConsumerAgent] = []

    for agent_id in range(size):
        age = int(rng.integers(18, 46))
        occupation = str(rng.choice(OCCUPATIONS))

        age_income_effect = (age - 18) / 40
        occupation_effect = 0.15 if occupation in {
            "Software Professional",
            "Business Professional",
            "Healthcare Professional",
        } else -0.08 if occupation == "Student" else 0.0

        income_score = clip01(
            0.30 + age_income_effect * 0.35 + occupation_effect + rng.normal(0, 0.14)
        )
        price_sensitivity = clip01(0.80 - 0.52 * income_score + rng.normal(0, 0.12))
        technology_adoption = clip01(
            0.78 - ((age - 18) / 27) * 0.20 + rng.normal(0, 0.16)
        )
        stubbornness = clip01(float(rng.beta(2.2, 2.8)))
        sociability = clip01(float(rng.beta(2.2, 2.2)))
        emotionality = clip01(float(rng.beta(2.2, 2.2)))
        logicality = clip01(0.85 - emotionality * 0.45 + rng.normal(0, 0.13))
        influence_power = clip01(0.10 + 0.55 * sociability + rng.normal(0, 0.10))
        product_need = clip01(float(rng.beta(2.0, 2.0)))
        risk_tolerance = clip01(float(rng.beta(2.0, 2.5)))
        brand_loyalty = clip01(float(rng.beta(1.8, 2.4)))

        traits_record = AgentTraits(
            sociability=sociability,
            price_sensitivity=price_sensitivity,
            technology_adoption=technology_adoption,
            emotionality=emotionality,
            logicality=logicality,
            stubbornness=stubbornness,
            influence_power=influence_power,
            product_need=product_need,
            risk_tolerance=risk_tolerance,
            brand_loyalty=brand_loyalty,
        )

        state = AgentState(
            confidence=clip01(float(rng.normal(0.52, 0.14))),
            knowledge=0.0,
            product_salience=clip01(float(rng.normal(0.65, 0.10))),
        )

        agent = ConsumerAgent(
            agent_id=agent_id,
            age=age,
            occupation=occupation,
            income_score=income_score,
            traits=traits_record,
            state=state,
        )
        agents.append(agent)
        if audit is not None:
            audit.emit(
                "population.agent_generated",
                {
                    "source": "bootstrap",
                    "generation_inputs": {
                        "occupation": occupation,
                        "age": age,
                        "age_income_effect": age_income_effect,
                        "occupation_effect": occupation_effect,
                    },
                    "agent": agent,
                },
                agent_ids=[agent_id],
            )

    return agents
