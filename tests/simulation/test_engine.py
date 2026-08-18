from copy import deepcopy

from simulation.conversation.router import ConversationRouter
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


def test_engine_records_bounded_replay_checkpoints_with_stable_agent_ids():
    result = run_small_simulation(seed=17, rounds=4)

    assert len(result.checkpoints) == 5
    assert result.checkpoints[0].round_index == 0
    assert result.checkpoints[0].active_conversation_ids == ()

    baseline_ids = tuple(state.agent_id for state in result.checkpoints[0].agent_states)
    assert 0 < len(baseline_ids) <= 80
    for checkpoint in result.checkpoints:
        assert tuple(state.agent_id for state in checkpoint.agent_states) == baseline_ids

    ledger_by_round = {
        round_index: {
            entry.conversation_id
            for entry in result.conversations
            if entry.round_index == round_index
        }
        for round_index in range(1, 5)
    }
    for checkpoint in result.checkpoints[1:]:
        assert set(checkpoint.active_conversation_ids) == ledger_by_round[checkpoint.round_index]


def test_final_replay_checkpoint_matches_final_sampled_agent_state():
    result = run_small_simulation(seed=23, rounds=3)
    final_by_id = {agent.agent_id: agent for agent in result.population}

    for state in result.checkpoints[-1].agent_states:
        agent = final_by_id[state.agent_id]
        assert state.overall_opinion == agent.state.overall_opinion
        assert state.purchase_intent == agent.state.purchase_intent
        assert state.confidence == agent.state.confidence


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


def test_engine_ledger_carries_python_owned_consumer_price_context():
    population = generate_population(40, seed=31)
    product = ProductKnowledge(
        name="AI Fitness Coach",
        category="Fitness Technology",
        pitch="Personalized workouts and nutrition guidance.",
        price=200,
        currency="INR",
        billing_cadence="monthly",
    )

    result = SimulationEngine().run(
        product=product,
        population=population,
        config=SimulationConfig(rounds=2, seed=31, k=6),
    )

    assert result.conversations
    entry = result.conversations[0]
    assert entry.language_context.agent_a_price_context is not None
    assert entry.language_context.agent_b_price_context is not None
    assert entry.language_context.agent_a_price_context.billing_cadence.value == "monthly"
    assert entry.language_context.agent_b_price_context.billing_cadence.value == "monthly"


class _HistoryObservingRouter(ConversationRouter):
    def __init__(self):
        self.saw_prior_topic_history = False

    def generate(self, pair, context):
        if context.recent_topics_by_agent or context.recent_topics_by_edge:
            self.saw_prior_topic_history = True
        return super().generate(pair, context)


def test_engine_supplies_completed_prior_round_topic_history_to_conversations():
    population = generate_population(60, seed=52)
    product = ProductKnowledge(
        name="AI Fitness Coach",
        category="Fitness Technology",
        pitch="Personalized workouts and nutrition guidance.",
        price=500,
        billing_cadence="monthly",
    )
    router = _HistoryObservingRouter()

    SimulationEngine(conversation_router=router).run(
        product=product,
        population=population,
        config=SimulationConfig(rounds=4, seed=52, k=7, initiator_rate=0.35),
    )

    assert router.saw_prior_topic_history is True


def test_engine_states_remain_bounded():
    result = run_small_simulation(seed=11, rounds=5)

    for agent in result.population:
        assert -1.0 <= agent.state.overall_opinion <= 1.0
        assert 0.0 <= agent.state.purchase_intent <= 1.0
        assert 0.0 <= agent.state.confidence <= 1.0
        assert all(-1.0 <= value <= 1.0 for value in agent.state.beliefs.as_dict().values())
