from enum import StrEnum

from pydantic import BaseModel, Field, model_validator

from simulation.product.pricing import BillingCadence


class PopulationMode(StrEnum):
    small = "small"
    standard = "standard"
    large = "large"


class DialogueMode(StrEnum):
    economy = "economy"
    balanced = "balanced"
    full = "full"
    full_live = "full_live"


_WEB_ROUND_LIMITS: dict[PopulationMode, int] = {
    PopulationMode.small: 100,
    PopulationMode.standard: 50,
    PopulationMode.large: 20,
}


class ProductPitchInput(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    category: str = Field(default="General", max_length=120)
    pitch: str = Field(min_length=10, max_length=12000)
    price: float | None = Field(default=None, ge=0)
    currency: str = Field(default="INR", min_length=3, max_length=3)
    billing_cadence: BillingCadence = BillingCadence.auto


class AdvancedSimulationConfig(BaseModel):
    population_size: int = Field(ge=2, le=5_000)
    base_k: int = Field(ge=1, le=128)
    max_conversations_per_round: int = Field(ge=1, le=8)
    initiator_rate: float = Field(ge=0.0, le=1.0)
    weak_tie_rate: float = Field(ge=0.0, le=1.0)
    simulated_minutes_per_round: int = Field(ge=1, le=1_440)


class SimulationPreviewRequest(BaseModel):
    product: ProductPitchInput
    population_mode: PopulationMode = PopulationMode.standard
    dialogue_mode: DialogueMode = DialogueMode.balanced
    rounds: int = Field(default=20, ge=1, le=100)
    seed: int = Field(default=42, ge=0, le=2_147_483_647)
    advanced_config: AdvancedSimulationConfig | None = None

    @model_validator(mode="after")
    def enforce_synchronous_web_budget(self) -> "SimulationPreviewRequest":
        if self.advanced_config is None:
            max_rounds = _WEB_ROUND_LIMITS[self.population_mode]
            if self.rounds > max_rounds:
                raise ValueError(
                    f"{self.population_mode.value} population is limited to "
                    f"{max_rounds} synchronous web rounds"
                )
        elif self.advanced_config.base_k >= self.advanced_config.population_size:
            raise ValueError("advanced base_k must be less than population_size")

        from backend.app.services.simulation_config_service import (
            MAX_SIMULATION_WORKLOAD,
            estimate_conversation_upper_bound,
        )

        upper_bound = estimate_conversation_upper_bound(self)
        if upper_bound > MAX_SIMULATION_WORKLOAD:
            raise ValueError(
                f"simulation workload upper bound {upper_bound} conversations exceeds "
                f"maximum allowed {MAX_SIMULATION_WORKLOAD}"
            )
        return self


class FullLiveSimulationRequest(SimulationPreviewRequest):
    full_live_confirmed: bool = False
    llm_provider: str = Field(min_length=1, max_length=40)
    llm_model: str = Field(min_length=1, max_length=200)

    @model_validator(mode="after")
    def validate_full_live_confirmation(self) -> "FullLiveSimulationRequest":
        if self.dialogue_mode is not DialogueMode.full_live:
            raise ValueError("Full Live endpoint requires dialogue_mode=full_live")
        if not self.full_live_confirmed:
            raise ValueError("Full Live requires explicit confirmation")
        return self


class FullLiveStartResponse(BaseModel):
    job_id: str
    status: str
    estimated_upper_bound_conversations: int
    llm_provider: str
    llm_model: str


class FullLiveStatusView(BaseModel):
    job_id: str
    status: str
    product_name: str
    population_mode: str
    rounds: int
    seed: int
    estimated_upper_bound_conversations: int
    llm_provider: str
    llm_model: str
    total_conversations: int | None = None
    processed_conversations: int = 0
    successful_renders: int = 0
    fallback_count: int = 0
    progress_ratio: float = 0.0
    prompt_tokens: int = 0
    prompt_cache_hit_tokens: int = 0
    prompt_cache_miss_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cache_hit_ratio: float = 0.0
    average_latency_ms: float = 0.0
    max_latency_ms: float = 0.0
    estimated_cost_usd: float = 0.0
    provider_model: str | None = None
    error_message: str | None = None
    cancel_requested: bool = False


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
    billing_cadence: BillingCadence
    advanced_config_enabled: bool
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


class ConversationTranscriptMessageView(BaseModel):
    speaker_id: int
    text: str


class ConversationView(BaseModel):
    round: int
    conversation_id: str
    agent_a_id: int
    agent_b_id: int
    topics: list[str]
    transcript: list[ConversationTranscriptMessageView]
    language_source: str
    importance: float
    llm_selected: bool


class DialogueStatsView(BaseModel):
    total_conversations: int
    selected_for_llm: int
    llm_rendered: int
    fallback_count: int
    background_count: int
    provider_available: bool
    provider_model: str | None = None
    prompt_tokens: int = 0
    prompt_cache_hit_tokens: int = 0
    prompt_cache_miss_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cache_hit_ratio: float = 0.0
    average_latency_ms: float = 0.0
    max_latency_ms: float = 0.0
    estimated_cost_usd: float = 0.0


class ReplayAgentStateView(BaseModel):
    id: int
    opinion: float
    purchase_intent: float
    confidence: float


class ReplayConversationEdgeView(BaseModel):
    conversation_id: str
    source: int
    target: int


class ReplayCheckpointView(BaseModel):
    round: int
    simulated_minutes: int
    nodes: list[ReplayAgentStateView]
    active_conversations: list[ReplayConversationEdgeView]


class PurchaseIntentDistributionView(BaseModel):
    low: int
    medium: int
    high: int


class TopicPressurePointView(BaseModel):
    topic: str
    raw_score: float
    normalized_score: float
    support_score: float
    criticism_score: float
    net_score: float
    normalized_support: float
    normalized_criticism: float


class DashboardAnalyticsView(BaseModel):
    purchase_intent_distribution: PurchaseIntentDistributionView
    topic_pressure: list[TopicPressurePointView]


class SimulationRunResponse(BaseModel):
    synthetic: bool
    status: str
    product_name: str
    billing_cadence: BillingCadence
    population_mode: PopulationMode
    advanced_config_enabled: bool
    dialogue_mode: DialogueMode
    llm_provider: str | None = None
    llm_model: str | None = None
    rounds: int
    seed: int
    preset: SimulationPresetView
    summary: SimulationSummaryView
    timeline: list[TimelinePointView]
    network: NetworkView
    selected_conversations: list[ConversationView]
    dialogue_stats: DialogueStatsView
    analytics: DashboardAnalyticsView
    replay: list[ReplayCheckpointView]
    trait_source: str
