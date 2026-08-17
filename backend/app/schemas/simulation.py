from enum import StrEnum

from pydantic import BaseModel, Field


class PopulationMode(StrEnum):
    small = "small"
    standard = "standard"
    large = "large"


class DialogueMode(StrEnum):
    economy = "economy"
    balanced = "balanced"
    full = "full"


class ProductPitchInput(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    category: str = Field(default="General", max_length=120)
    pitch: str = Field(min_length=10, max_length=12000)
    price: float | None = Field(default=None, ge=0)
    currency: str = Field(default="INR", min_length=3, max_length=3)


class SimulationPreviewRequest(BaseModel):
    product: ProductPitchInput
    population_mode: PopulationMode = PopulationMode.standard
    dialogue_mode: DialogueMode = DialogueMode.balanced
    rounds: int = Field(default=20, ge=1, le=200)
    seed: int = Field(default=42, ge=0, le=2_147_483_647)


class SimulationPresetView(BaseModel):
    population_size: int
    base_k: int
    max_conversations_per_round: int
    initiator_rate: float
    weak_tie_rate: float
    simulated_minutes_per_round: int


class SimulationPreviewResponse(BaseModel):
    status: str
    product_name: str
    preset: SimulationPresetView
    rounds: int
    dialogue_mode: DialogueMode
    seed: int
    note: str


class TimelinePointView(BaseModel):
    round: int
    mean_opinion: float
    mean_purchase_intent: float
    positive_share: float
    neutral_share: float
    negative_share: float
    conversation_count: int


class SimulationSummaryView(BaseModel):
    population_size: int
    conversation_count: int
    final_mean_opinion: float
    final_mean_purchase_intent: float
    base_k: int


class NetworkNodeView(BaseModel):
    id: int
    opinion: float
    purchase_intent: float
    influence: float
    segment: str


class NetworkEdgeView(BaseModel):
    source: int
    target: int
    similarity: float
    weak_tie: bool


class NetworkView(BaseModel):
    nodes: list[NetworkNodeView]
    edges: list[NetworkEdgeView]


class ConversationView(BaseModel):
    round: int
    conversation_id: str
    agent_a_id: int
    agent_b_id: int
    topics: list[str]


class SimulationRunResponse(BaseModel):
    synthetic: bool
    status: str
    product_name: str
    population_mode: PopulationMode
    dialogue_mode: DialogueMode
    rounds: int
    seed: int
    preset: SimulationPresetView
    summary: SimulationSummaryView
    timeline: list[TimelinePointView]
    network: NetworkView
    selected_conversations: list[ConversationView]
    trait_source: str
