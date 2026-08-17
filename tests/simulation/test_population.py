from simulation.population.generator import generate_population


def test_population_is_reproducible_and_bounded() -> None:
    first = generate_population(20, seed=7)
    second = generate_population(20, seed=7)

    assert [agent.age for agent in first] == [agent.age for agent in second]
    assert [agent.income_score for agent in first] == [agent.income_score for agent in second]

    for agent in first:
        assert 18 <= agent.age <= 45
        assert 0.0 <= agent.income_score <= 1.0
        assert all(0.0 <= value <= 1.0 for value in agent.traits.as_dict().values())
