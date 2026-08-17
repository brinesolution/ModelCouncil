from __future__ import annotations

import numpy as np

from simulation.domain.agent import AgentState, AgentTraits, ConsumerAgent
from simulation.population.correlations import (
    clip01,
    correlated_influence_power,
    correlated_logicality,
    correlated_price_sensitivity,
    jitter_normalized,
    sample_income,
)
from simulation.population.trait_repository import TraitCatalog, TraitRepository, TraitValue

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
        return _generate_bootstrap_population(size=size, rng=rng)
    return _generate_catalog_population(size=size, rng=rng, catalog=traits.load_catalog())


def _generate_catalog_population(
    size: int,
    rng: np.random.Generator,
    catalog: TraitCatalog,
) -> list[ConsumerAgent]:
    agents: list[ConsumerAgent] = []

    for agent_id in range(size):
        occupation = _sample(catalog, "occupations", rng)
        personality = _sample(catalog, "personality", rng)
        economic = _sample(catalog, "economic_traits", rng)
        social = _sample(catalog, "social_behaviour", rng)
        technology = _sample(catalog, "technology", rng)
        behaviour = _sample(catalog, "consumer_behaviour", rng)

        min_age = int(_number(occupation, "min_age", 18))
        max_age = max(min_age + 1, 55)
        age = int(rng.integers(min_age, max_age + 1))

        income_score = sample_income(
            rng,
            _number(occupation, "income_min", 0.15),
            _number(occupation, "income_max", 0.75),
            occupation.key,
        )

        emotionality = jitter_normalized(
            rng, _number(personality, "emotionality", 0.5), sigma=0.06
        )
        base_logicality = _number(personality, "logicality", 0.55)
        logicality = correlated_logicality(rng, base_logicality, emotionality)
        stubbornness = jitter_normalized(
            rng, _number(personality, "stubbornness", 0.5), sigma=0.06
        )
        risk_tolerance = jitter_normalized(
            rng, _number(personality, "risk_tolerance", 0.5), sigma=0.07
        )

        personality_social = _number(personality, "sociability", 0.5)
        social_profile = _number(social, "sociability", personality_social)
        sociability = jitter_normalized(
            rng, 0.35 * personality_social + 0.65 * social_profile, sigma=0.06
        )

        price_sensitivity = correlated_price_sensitivity(
            rng,
            _number(economic, "price_sensitivity", 0.55),
            income_score,
        )
        technology_adoption = jitter_normalized(
            rng, _number(technology, "technology_adoption", 0.55), sigma=0.06
        )
        influence_power = correlated_influence_power(
            rng,
            sociability=sociability,
            base_persuasion=_number(social, "persuasion_power", 0.45),
        )
        brand_loyalty = jitter_normalized(
            rng, _number(behaviour, "brand_loyalty", 0.45), sigma=0.07
        )
        product_need = clip01(float(rng.beta(2.0, 2.0)))

        state = AgentState(
            confidence=clip01(float(rng.normal(0.52, 0.14))),
            knowledge=0.0,
            product_salience=clip01(float(rng.normal(0.65, 0.10))),
        )
        agents.append(
            ConsumerAgent(
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
            )
        )

    return agents


def _sample(catalog: TraitCatalog, category: str, rng: np.random.Generator) -> TraitValue:
    values = catalog.category(category)
    probabilities = np.array([item.probability for item in values], dtype=float)
    index = int(rng.choice(len(values), p=probabilities / probabilities.sum()))
    return values[index]


def _number(value: TraitValue, attribute: str, default: float) -> float:
    raw = value.attributes.get(attribute, default)
    try:
        return float(raw)
    except (TypeError, ValueError):
        return default


def _generate_bootstrap_population(
    size: int,
    rng: np.random.Generator,
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

        agents.append(
            ConsumerAgent(
                agent_id=agent_id,
                age=age,
                occupation=occupation,
                income_score=income_score,
                traits=traits_record,
                state=state,
            )
        )

    return agents
