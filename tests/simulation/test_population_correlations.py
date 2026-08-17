import pytest

from simulation.population.generator import generate_population
from simulation.population.trait_repository import TraitCatalog, TraitCategory, TraitValue


class FixedTraitRepository:
    def load_catalog(self) -> TraitCatalog:
        return TraitCatalog(
            categories={
                "occupations": TraitCategory(
                    key="occupations",
                    values=(
                        TraitValue(
                            key="student",
                            label="Student",
                            probability=1.0,
                            attributes={
                                "min_age": 18,
                                "income_min": 0.05,
                                "income_max": 0.32,
                                "tech_exposure": 0.78,
                            },
                        ),
                    ),
                ),
                "personality": TraitCategory(
                    key="personality",
                    values=(
                        TraitValue(
                            key="analytical",
                            label="Analytical",
                            probability=1.0,
                            attributes={
                                "logicality": 0.88,
                                "emotionality": 0.28,
                                "stubbornness": 0.55,
                                "risk_tolerance": 0.42,
                                "sociability": 0.44,
                            },
                        ),
                    ),
                ),
                "economic_traits": TraitCategory(
                    key="economic_traits",
                    values=(
                        TraitValue(
                            key="budget_constrained",
                            label="Budget-constrained",
                            probability=1.0,
                            attributes={"price_sensitivity": 0.90},
                        ),
                    ),
                ),
                "social_behaviour": TraitCategory(
                    key="social_behaviour",
                    values=(
                        TraitValue(
                            key="normal_social",
                            label="Normally Social",
                            probability=1.0,
                            attributes={
                                "sociability": 0.56,
                                "persuasion_power": 0.48,
                            },
                        ),
                    ),
                ),
                "technology": TraitCategory(
                    key="technology",
                    values=(
                        TraitValue(
                            key="tech_savvy",
                            label="Tech Savvy",
                            probability=1.0,
                            attributes={"technology_adoption": 0.86},
                        ),
                    ),
                ),
                "consumer_behaviour": TraitCategory(
                    key="consumer_behaviour",
                    values=(
                        TraitValue(
                            key="researcher",
                            label="Heavy Researcher",
                            probability=1.0,
                            attributes={"brand_loyalty": 0.44},
                        ),
                    ),
                ),
            }
        )


def test_repository_population_preserves_student_income_range():
    population = generate_population(500, seed=8, traits=FixedTraitRepository())

    assert all(agent.occupation == "Student" for agent in population)
    assert max(agent.income_score for agent in population) <= 0.55
    assert min(agent.income_score for agent in population) >= 0.0


def test_repository_population_is_reproducible():
    first = generate_population(25, seed=19, traits=FixedTraitRepository())
    second = generate_population(25, seed=19, traits=FixedTraitRepository())

    assert first == second


def test_repository_traits_are_used_as_population_priors():
    population = generate_population(100, seed=3, traits=FixedTraitRepository())
    mean_tech = sum(a.traits.technology_adoption for a in population) / len(population)
    mean_price = sum(a.traits.price_sensitivity for a in population) / len(population)

    assert mean_tech == pytest.approx(0.86, abs=0.16)
    assert mean_price == pytest.approx(0.90, abs=0.16)
