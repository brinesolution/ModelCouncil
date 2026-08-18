from __future__ import annotations

import math
from dataclasses import dataclass

from simulation.conversation.ledger import ConversationLedgerEntry


@dataclass(frozen=True, slots=True)
class DialoguePolicy:
    fraction: float
    max_calls: int


_POLICIES = {
    "economy": DialoguePolicy(fraction=0.05, max_calls=6),
    "balanced": DialoguePolicy(fraction=0.20, max_calls=20),
    "full": DialoguePolicy(fraction=1.00, max_calls=48),
}


def get_dialogue_policy(mode: str) -> DialoguePolicy:
    try:
        return _POLICIES[mode]
    except KeyError as exc:
        raise ValueError(f"unknown dialogue mode: {mode}") from exc


def select_for_llm(
    entries: list[ConversationLedgerEntry],
    mode: str,
) -> tuple[str, ...]:
    if not entries:
        return ()

    policy = get_dialogue_policy(mode)
    requested = max(1, math.ceil(len(entries) * policy.fraction))
    limit = min(policy.max_calls, requested, len(entries))
    ranked = sorted(entries, key=lambda entry: (-entry.importance, entry.conversation_id))
    selected = ranked[:limit]
    return tuple(sorted(entry.conversation_id for entry in selected))
