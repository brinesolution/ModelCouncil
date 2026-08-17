from __future__ import annotations

import numpy as np

from simulation.domain.agent import AgentState, AgentTraits, ConsumerAgent

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


def _clip01(value: float) -> float:
    return float(np.clip(value, 0.0, 1.0))


def generate_population(size: int, seed: int = 42) -> list[ConsumerAgent]:
    """Generate the deterministic bootstrap population used before Excel traits land.

    This is intentionally a conservative bootstrap generator. The production trait
    pipeline will replace its distributions with configurable Excel-backed sources,
    while preserving the same ConsumerAgent contract.
    """
    if size < 2:
        raise ValueError("Population size must be at least 2.")

    rng = np.random.default_rng(seed)
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

        income_score = _clip01(
            0.30 + age_income_effect * 0.35 + occupation_effect + rng.normal(0, 0.14)
        )
        price_sensitivity = _clip01(0.80 - 0.52 * income_score + rng.normal(0, 0.12))
        technology_adoption = _clip01(
            0.78 - ((age - 18) / 27) * 0.20 + rng.normal(0, 0.16)
        )
        stubbornness = _clip01(rng.beta(2.2, 2.8))
        sociability = _clip01(rng.beta(2.2, 2.2))
        emotionality = _clip01(rng.beta(2.2, 2.2))
        logicality = _clip01(0.85 - emotionality * 0.45 + rng.normal(0, 0.13))
        influence_power = _clip01(0.10 + 0.55 * sociability + rng.normal(0, 0.10))
        product_need = _clip01(rng.beta(2.0, 2.0))
        risk_tolerance = _clip01(rng.beta(2.0, 2.5))
        brand_loyalty = _clip01(rng.beta(1.8, 2.4))

        traits = AgentTraits(
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
            confidence=_clip01(rng.normal(0.52, 0.14)),
            knowledge=0.0,
            product_salience=_clip01(rng.normal(0.65, 0.10)),
        )

        agents.append(
            ConsumerAgent(
                agent_id=agent_id,
                age=age,
                occupation=occupation,
                income_score=income_score,
                traits=traits,
                state=state,
            )
        )

    return agents
