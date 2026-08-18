from __future__ import annotations

from simulation.conversation.ledger import ConversationLedgerEntry


def score_conversation(entry: ConversationLedgerEntry) -> float:
    """Return a transparent bounded importance score for language rendering."""
    profiles = (entry.language_context.agent_a, entry.language_context.agent_b)
    average_influence = sum(profile.influence_power for profile in profiles) / 2.0
    average_receptivity = sum(1.0 - profile.stubbornness for profile in profiles) / 2.0
    disagreement = min(
        1.0,
        abs(profiles[0].overall_opinion - profiles[1].overall_opinion) / 2.0,
    )

    stance_values = [
        abs(stance)
        for message in entry.result.messages
        for stance in message.topic_effects.values()
    ]
    semantic_intensity = (
        sum(stance_values) / len(stance_values) if stance_values else 0.0
    )

    score = (
        0.16 * entry.pair.edge_score
        + 0.18 * average_influence
        + 0.14 * average_receptivity
        + 0.14 * entry.trust
        + 0.10 * entry.relationship_strength
        + 0.18 * semantic_intensity
        + 0.06 * disagreement
        + 0.04 * float(entry.weak_tie)
    )
    return max(0.0, min(1.0, float(score)))
