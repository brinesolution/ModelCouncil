from __future__ import annotations

from dataclasses import dataclass
from statistics import median, pstdev

from simulation.conversation.ledger import ConversationLedgerEntry
from simulation.domain.agent import ConsumerAgent


@dataclass(frozen=True, slots=True)
class SocialDynamicsMetrics:
    mean_absolute_opinion_movement: float
    median_absolute_opinion_movement: float
    upward_movers: int
    downward_movers: int
    unchanged_agents: int
    initial_opinion_std: float
    final_opinion_std: float
    mean_contact_opinion_gap: float
    selected_weak_tie_share: float


def compute_social_dynamics_metrics(
    initial_opinions: dict[int, float],
    final_agents: list[ConsumerAgent],
    ledger: list[ConversationLedgerEntry],
) -> SocialDynamicsMetrics:
    final_by_id = {agent.agent_id: agent.state.overall_opinion for agent in final_agents}
    common = sorted(initial_opinions.keys() & final_by_id.keys())
    movements = [final_by_id[agent_id] - initial_opinions[agent_id] for agent_id in common]
    absolute = [abs(value) for value in movements]
    epsilon = 1e-12

    contact_gaps = [
        abs(entry.language_context.agent_a.overall_opinion - entry.language_context.agent_b.overall_opinion)
        / 2.0
        for entry in ledger
    ]
    weak_count = sum(1 for entry in ledger if entry.weak_tie)

    initial_values = [initial_opinions[agent_id] for agent_id in common]
    final_values = [final_by_id[agent_id] for agent_id in common]
    return SocialDynamicsMetrics(
        mean_absolute_opinion_movement=(sum(absolute) / len(absolute) if absolute else 0.0),
        median_absolute_opinion_movement=(float(median(absolute)) if absolute else 0.0),
        upward_movers=sum(1 for value in movements if value > epsilon),
        downward_movers=sum(1 for value in movements if value < -epsilon),
        unchanged_agents=sum(1 for value in movements if abs(value) <= epsilon),
        initial_opinion_std=(float(pstdev(initial_values)) if len(initial_values) > 1 else 0.0),
        final_opinion_std=(float(pstdev(final_values)) if len(final_values) > 1 else 0.0),
        mean_contact_opinion_gap=(sum(contact_gaps) / len(contact_gaps) if contact_gaps else 0.0),
        selected_weak_tie_share=(weak_count / len(ledger) if ledger else 0.0),
    )
