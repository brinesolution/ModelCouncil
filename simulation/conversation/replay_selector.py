from __future__ import annotations

from collections import Counter

from simulation.conversation.ledger import ConversationLedgerEntry


def select_replay_conversations(
    entries: list[ConversationLedgerEntry],
    *,
    limit: int = 12,
) -> list[ConversationLedgerEntry]:
    """Select a high-importance but non-monocultural replay sample.

    This is a display-only selector. It never changes conversation importance, ledger
    history, dialogue selection, or Full Live rendering.
    """
    if limit <= 0 or not entries:
        return []

    remaining = sorted(
        entries,
        key=lambda entry: (-entry.importance, entry.conversation_id),
    )
    if len(remaining) <= limit:
        return remaining

    selected: list[ConversationLedgerEntry] = [remaining.pop(0)]
    topic_counts = Counter(_primary_topic(selected[0]) for _ in (0,))
    seen_directions = {_stance_direction(selected[0])}
    seen_rounds = {selected[0].round_index}
    has_weak_tie = selected[0].weak_tie

    while remaining and len(selected) < limit:
        best_index = 0
        best_score = float("-inf")
        best_id = ""
        for index, candidate in enumerate(remaining):
            topic = _primary_topic(candidate)
            direction = _stance_direction(candidate)
            score = float(candidate.importance)

            if topic_counts[topic] == 0:
                score += 0.12
            else:
                score -= min(0.18, 0.045 * topic_counts[topic])
            if direction not in seen_directions:
                score += 0.07
            if candidate.round_index not in seen_rounds:
                score += 0.04
            if candidate.weak_tie and not has_weak_tie:
                score += 0.04

            if score > best_score or (
                score == best_score and candidate.conversation_id < best_id
            ):
                best_index = index
                best_score = score
                best_id = candidate.conversation_id

        chosen = remaining.pop(best_index)
        selected.append(chosen)
        topic_counts[_primary_topic(chosen)] += 1
        seen_directions.add(_stance_direction(chosen))
        seen_rounds.add(chosen.round_index)
        has_weak_tie = has_weak_tie or chosen.weak_tie

    return selected


def _primary_topic(entry: ConversationLedgerEntry) -> str:
    totals: dict[str, float] = {}
    for message in entry.result.messages:
        for topic, stance in message.topic_effects.items():
            totals[topic] = totals.get(topic, 0.0) + abs(float(stance))
    if not totals:
        return "general"
    return max(totals.items(), key=lambda item: (item[1], item[0]))[0]


def _stance_direction(entry: ConversationLedgerEntry) -> str:
    stances = [
        float(stance)
        for message in entry.result.messages
        for stance in message.topic_effects.values()
    ]
    if not stances:
        return "mixed"
    mean = sum(stances) / len(stances)
    if mean > 0.12:
        return "supportive"
    if mean < -0.12:
        return "critical"
    return "mixed"
