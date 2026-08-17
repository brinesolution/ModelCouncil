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

export interface SimulationConversation {
  round: number;
  conversation_id: string;
  agent_a_id: number;
  agent_b_id: number;
  topics: string[];
}

export interface SimulationRunResponse {
  synthetic: true;
  status: string;
  product_name: string;
  population_mode: PopulationMode;
  dialogue_mode: DialogueMode;
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
  trait_source: string;
}
