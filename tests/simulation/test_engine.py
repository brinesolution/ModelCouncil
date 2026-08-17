from copy import deepcopy

from simulation.engine import SimulationConfig, SimulationEngine
from simulation.population.generator import generate_population
from simulation.product.knowledge import ProductKnowledge


def run_small_simulation(seed: int, rounds: int = 3):
    population = generate_population(40, seed=seed)
    product = ProductKnowledge(
        name="AI Fitness Coach",
        pitch="Personalized workouts, nutrition guidance, and progress tracking.",
        price=999,
        currency="INR",
    )
    return SimulationEngine().run(
        product=product,
        population=population,
        config=SimulationConfig(
            rounds=rounds,
            seed=seed,
            k=6,
            max_conversations_per_agent=2,
            initiator_rate=0.20,
            weak_tie_rate=0.05,
        ),
    )


def test_engine_same_seed_produces_same_timeline():
    first = run_small_simulation(seed=42, rounds=3)
    second = run_small_simulation(seed=42, rounds=3)

    assert first.timeline == second.timeline
    assert first.conversation_count == second.conversation_count


def test_engine_records_baseline_plus_each_round():
    result = run_small_simulation(seed=5, rounds=4)

    assert len(result.timeline) == 5
    assert result.timeline[0].round_index == 0
    assert result.timeline[-1].round_index == 4
    assert result.synthetic is True


def test_engine_does_not_mutate_input_population():
    population = generate_population(30, seed=7)
    original = deepcopy(population)
    product = ProductKnowledge(name="Test", pitch="A useful product pitch with enough detail.")

    SimulationEngine().run(
        product=product,
        population=population,
        config=SimulationConfig(rounds=2, seed=7, k=5),
    )

    assert population == original


def test_engine_states_remain_bounded():
    result = run_small_simulation(seed=11, rounds=5)

    for agent in result.population:
        assert -1.0 <= agent.state.overall_opinion <= 1.0
        assert 0.0 <= agent.state.purchase_intent <= 1.0
        assert 0.0 <= agent.state.confidence <= 1.0
        assert all(-1.0 <= value <= 1.0 for value in agent.state.beliefs.as_dict().values())
