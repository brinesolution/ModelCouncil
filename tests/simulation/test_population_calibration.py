from pathlib import Path

import numpy as np

from simulation.population.excel_repository import ExcelTraitRepository
from simulation.population.generator import generate_population


TRAIT_ROOT = Path("data/traits")


def _corr(agents, left: str, right: str) -> float:
    a = np.asarray([getattr(agent.traits, left) for agent in agents], dtype=float)
    b = np.asarray([getattr(agent.traits, right) for agent in agents], dtype=float)
    return float(np.corrcoef(a, b)[0, 1])


def test_population_trait_correlations_remain_plausible_not_near_deterministic():
    agents = generate_population(5000, seed=1801, traits=ExcelTraitRepository(TRAIT_ROOT))

    emotional_logical = _corr(agents, "emotionality", "logicality")
    social_influence = _corr(agents, "sociability", "influence_power")
    stubborn_risk = _corr(agents, "stubbornness", "risk_tolerance")

    assert abs(emotional_logical) < 0.75
    assert social_influence < 0.70
    assert abs(stubborn_risk) < 0.70

    # Preserve broad intended direction without making one trait a proxy for another.
    assert emotional_logical < -0.10
    assert social_influence > 0.10
    assert stubborn_risk < -0.10


def test_population_trait_ranges_remain_broad_after_correlation_calibration():
    agents = generate_population(5000, seed=1802, traits=ExcelTraitRepository(TRAIT_ROOT))

    for name in (
        "emotionality",
        "logicality",
        "sociability",
        "influence_power",
        "stubbornness",
        "risk_tolerance",
    ):
        values = np.asarray([getattr(agent.traits, name) for agent in agents], dtype=float)
        assert float(np.std(values)) > 0.10
        assert float(np.quantile(values, 0.90) - np.quantile(values, 0.10)) > 0.25
