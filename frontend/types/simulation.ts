export type PopulationMode = "small" | "standard" | "large";
export type DialogueMode = "economy" | "balanced" | "full" | "full_live";
export type BillingCadence = "auto" | "one_time" | "monthly" | "yearly";

export const WEB_ROUND_LIMITS: Record<PopulationMode, number> = {
  small: 100,
  standard: 50,
  large: 20,
};

export interface AdvancedSimulationConfig {
  population_size: number;
  base_k: number;
  max_conversations_per_round: number;
  initiator_rate: number;
  weak_tie_rate: number;
  simulated_minutes_per_round: number;
}

export interface SimulationPreviewRequest {
  product: {
    name: string;
    category: string;
    pitch: string;
    price: number | null;
    currency: string;
    billing_cadence: BillingCadence;
  };
  population_mode: PopulationMode;
  dialogue_mode: DialogueMode;
  rounds: number;
  seed: number;
  advanced_config?: AdvancedSimulationConfig | null;
}

export interface SimulationPreviewResponse {
  status: string;
  product_name: string;
  billing_cadence: Exclude<BillingCadence, "auto">;
  advanced_config_enabled: boolean;
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
