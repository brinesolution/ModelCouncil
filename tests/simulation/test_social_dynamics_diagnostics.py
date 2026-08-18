from copy import deepcopy

import pytest

from simulation.analytics.social_dynamics import compute_social_dynamics_metrics
from simulation.conversation.ledger import ConversationLanguageContext, ConversationLedgerEntry
from simulation.conversation.models import ConversationPair, ConversationResult
from simulation.population.generator import generate_population


def test_diagnostics_detect_symmetric_individual_movement_when_population_mean_is_stable():
    initial_agents = generate_population(4, seed=77)
    for agent, opinion in zip(initial_agents, (-0.4, -0.2, 0.2, 0.4), strict=True):
        agent.state.overall_opinion = opinion
    initial = {agent.agent_id: agent.state.overall_opinion for agent in initial_agents}
    final_agents = deepcopy(initial_agents)
    for agent, opinion in zip(final_agents, (-0.3, -0.1, 0.1, 0.3), strict=True):
        agent.state.overall_opinion = opinion

    metrics = compute_social_dynamics_metrics(initial, final_agents, [])

    assert sum(initial.values()) / 4 == pytest.approx(sum(a.state.overall_opinion for a in final_agents) / 4)
    assert metrics.mean_absolute_opinion_movement == pytest.approx(0.10)
    assert metrics.median_absolute_opinion_movement == pytest.approx(0.10)
    assert metrics.upward_movers == 2
    assert metrics.downward_movers == 2
    assert metrics.unchanged_agents == 0
    assert metrics.final_opinion_std < metrics.initial_opinion_std


def test_diagnostics_measure_contact_gap_and_weak_tie_share():
    agents = generate_population(2, seed=78)
    agents[0].state.overall_opinion = -0.6
    agents[1].state.overall_opinion = 0.4
    context = ConversationLanguageContext.from_agents(agents[0], agents[1])
    ledger = [
        ConversationLedgerEntry(
            round_index=1,
            pair=ConversationPair("r1-a0-a1", 1, 0, 1, 0.5),
            result=ConversationResult("r1-a0-a1", [], [], "background"),
            language_context=context,
            trust=0.3,
            relationship_strength=0.3,
            similarity=0.2,
            weak_tie=True,
        )
    ]

    metrics = compute_social_dynamics_metrics(
        {0: -0.6, 1: 0.4},
        agents,
        ledger,
    )

    assert metrics.mean_contact_opinion_gap == pytest.approx(0.5)
    assert metrics.selected_weak_tie_share == pytest.approx(1.0)
