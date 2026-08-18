from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class ConversationPair:
    conversation_id: str
    round_index: int
    agent_a_id: int
    agent_b_id: int
    edge_score: float


@dataclass(frozen=True, slots=True)
class SemanticMessage:
    speaker_id: int
    listener_id: int
    topic_effects: dict[str, float]
    argument_strength: float
    confidence: float
    text: str | None = None
    claims: tuple[str, ...] = ()


@dataclass(slots=True)
class ConversationResult:
    conversation_id: str
    messages: list[SemanticMessage] = field(default_factory=list)
    transcript: list[dict[str, str | int]] = field(default_factory=list)
    language_source: str = "background"
