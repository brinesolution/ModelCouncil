import type { DialogueMode, PopulationMode, SimulationPreviewResponse } from "@/types/simulation";

export interface SimulationTimelinePoint {
  round: number;
  mean_opinion: number;
  mean_purchase_intent: number;
  positive_share: number;
  neutral_share: number;
  negative_share: number;
  conversation_count: number;
}

export interface SimulationNetworkNode {
  id: number;
  opinion: number;
  purchase_intent: number;
  influence: number;
  segment: string;
}

export interface SimulationNetworkEdge {
  source: number;
  target: number;
  similarity: number;
  weak_tie: boolean;
}

export interface SimulationConversationMessage {
  speaker_id: number;
  text: string;
}

export interface SimulationConversation {
  round: number;
  conversation_id: string;
  agent_a_id: number;
  agent_b_id: number;
  topics: string[];
  transcript: SimulationConversationMessage[];
  language_source: string;
  importance: number;
  llm_selected: boolean;
}

export interface DialogueRenderStats {
  total_conversations: number;
  selected_for_llm: number;
  llm_rendered: number;
  fallback_count: number;
  background_count: number;
  provider_available: boolean;
  provider_model: string | null;
  prompt_tokens: number;
  prompt_cache_hit_tokens: number;
  prompt_cache_miss_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  cache_hit_ratio: number;
  average_latency_ms: number;
  max_latency_ms: number;
  estimated_cost_usd: number;
}

export interface SimulationReplayAgentState {
  id: number;
  opinion: number;
  purchase_intent: number;
  confidence: number;
}

export interface SimulationReplayConversation {
  conversation_id: string;
  source: number;
  target: number;
}

export interface SimulationReplayCheckpoint {
  round: number;
  simulated_minutes: number;
  nodes: SimulationReplayAgentState[];
  active_conversations: SimulationReplayConversation[];
}

export interface PurchaseIntentDistribution {
  low: number;
  medium: number;
  high: number;
}

export interface TopicPressurePoint {
  topic: string;
  raw_score: number;
  normalized_score: number;
  support_score?: number;
  criticism_score?: number;
  net_score?: number;
  normalized_support?: number;
  normalized_criticism?: number;
}

export interface DashboardAnalytics {
  purchase_intent_distribution: PurchaseIntentDistribution;
  topic_pressure: TopicPressurePoint[];
}

export interface SimulationRunResponse {
  synthetic: true;
  status: string;
  product_name: string;
  billing_cadence: "one_time" | "monthly" | "yearly";
  population_mode: PopulationMode;
  advanced_config_enabled: boolean;
  dialogue_mode: DialogueMode;
  llm_provider: string | null;
  llm_model: string | null;
  rounds: number;
  seed: number;
  preset: SimulationPreviewResponse["preset"];
  summary: {
    population_size: number;
    conversation_count: number;
    final_mean_opinion: number;
    final_mean_purchase_intent: number;
    base_k: number;
  };
  timeline: SimulationTimelinePoint[];
  network: {
    nodes: SimulationNetworkNode[];
    edges: SimulationNetworkEdge[];
  };
  selected_conversations: SimulationConversation[];
  dialogue_stats: DialogueRenderStats;
  analytics: DashboardAnalytics;
  replay: SimulationReplayCheckpoint[];
  trait_source: string;
}
