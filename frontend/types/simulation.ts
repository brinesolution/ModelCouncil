export type PopulationMode = "small" | "standard" | "large";
export type DialogueMode = "economy" | "balanced" | "full";

export interface SimulationPreviewRequest {
  product: {
    name: string;
    category: string;
    pitch: string;
    price: number | null;
    currency: string;
  };
  population_mode: PopulationMode;
  dialogue_mode: DialogueMode;
  rounds: number;
  seed: number;
}

export interface SimulationPreviewResponse {
  status: string;
  product_name: string;
  preset: {
    population_size: number;
    base_k: number;
    max_conversations_per_round: number;
    initiator_rate: number;
    weak_tie_rate: number;
    simulated_minutes_per_round: number;
  };
  rounds: number;
  dialogue_mode: DialogueMode;
  seed: number;
  note: string;
}
