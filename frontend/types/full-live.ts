import type { SimulationPreviewRequest } from "@/types/simulation";

export type FullLiveJobStatus =
  | "queued"
  | "simulating"
  | "rendering"
  | "cancelling"
  | "cancelled"
  | "completed"
  | "failed";

export interface FullLiveSimulationRequest extends SimulationPreviewRequest {
  dialogue_mode: "full_live";
  full_live_confirmed: true;
  llm_provider: string;
  llm_model: string;
}

export interface FullLiveStartResponse {
  job_id: string;
  status: "queued";
  estimated_upper_bound_conversations: number;
  llm_provider: string;
  llm_model: string;
}

export interface FullLiveStatusResponse {
  job_id: string;
  status: FullLiveJobStatus;
  product_name: string;
  population_mode: string;
  rounds: number;
  seed: number;
  estimated_upper_bound_conversations: number;
  llm_provider: string;
  llm_model: string;
  total_conversations: number | null;
  processed_conversations: number;
  successful_renders: number;
  fallback_count: number;
  progress_ratio: number;
  prompt_tokens: number;
  prompt_cache_hit_tokens: number;
  prompt_cache_miss_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  cache_hit_ratio: number;
  average_latency_ms: number;
  max_latency_ms: number;
  estimated_cost_usd: number;
  provider_model: string | null;
  error_message: string | null;
  cancel_requested: boolean;
}
