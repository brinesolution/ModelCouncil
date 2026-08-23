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
  social_layers: string[];
  primary_layer: string;
}

export interface SimulationConversationMessage {
  speaker_id: number;
  text: string;
}

export interface SimulationAgentTraits {
  sociability: number;
  price_sensitivity: number;
  technology_adoption: number;
  emotionality: number;
  logicality: number;
  stubbornness: number;
  influence_power: number;
  product_need: number;
  risk_tolerance: number;
  brand_loyalty: number;
}

export interface SimulationSocialMemberships {
  region_id: string;
  city_id: string;
  city_tier: number;
  locality_id: string;
  household_id: string | null;
  workplace_id: string | null;
  education_id: string | null;
  online_interest_ids: string[];
}

export interface SimulationAgentProfile {
  agent_id: number;
  age: number;
  occupation: string;
  income_score: number;
  primary_language: string;
  locale: string;
  archetype_key: string;
  demographic_key: string;
  occupation_key: string;
  memberships: SimulationSocialMemberships;
  traits: SimulationAgentTraits;
}

export interface SimulationConversation {
  round: number;
  conversation_id: string;
  agent_a_id: number;
  agent_b_id: number;
  agent_a_profile: SimulationAgentProfile;
  agent_b_profile: SimulationAgentProfile;
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

export interface OpinionDiagnostics {
  below_zero_share: number;
  strong_negative_share: number;
  minimum: number;
  median: number;
  maximum: number;
  strong_negative_threshold: number;
}

export interface DashboardAnalytics {
  purchase_intent_distribution: PurchaseIntentDistribution;
  opinion_diagnostics: OpinionDiagnostics;
  topic_pressure: TopicPressurePoint[];
}

export interface SimulationNetworkMetrics {
  node_count: number;
  edge_count: number;
  mean_degree: number;
  median_degree: number;
  degree_std: number;
  degree_p10: number;
  degree_p90: number;
  degree_p99: number;
  max_degree: number;
  degree_gini: number;
  target_degree_mean: number;
  target_degree_std: number;
  connected_components: number;
  largest_component_share: number;
  clustering_coefficient: number;
  weak_tie_share: number;
  structured_weak_tie_share: number;
  cross_community_edge_share: number;
  similarity_mean: number;
  similarity_std: number;
  similarity_p10: number;
  similarity_p90: number;
  relationship_mean: number;
  relationship_std: number;
  directional_trust_mean: number;
  directional_trust_std: number;
  household_edge_share: number;
  workplace_edge_share: number;
  local_edge_share: number;
  education_edge_share: number;
  online_edge_share: number;
  affinity_edge_share: number;
  multi_layer_edge_share: number;
  household_membership_share: number;
  workplace_membership_share: number;
  education_membership_share: number;
  online_membership_share: number;
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
    metrics: SimulationNetworkMetrics;
  };
  selected_conversations: SimulationConversation[];
  dialogue_stats: DialogueRenderStats;
  analytics: DashboardAnalytics;
  replay: SimulationReplayCheckpoint[];
  trait_source: string;
}
