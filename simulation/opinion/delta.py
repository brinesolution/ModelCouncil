from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class AgentStateDelta:
    belief_updates: dict[str, float] = field(default_factory=dict)
    confidence_delta: float = 0.0
    knowledge_delta: float = 0.0
    salience_delta: float = 0.0
