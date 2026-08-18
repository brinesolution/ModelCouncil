import type {
  AdvancedSimulationConfig,
  PopulationMode,
} from "../types/simulation";

export const MAX_SIMULATION_WORKLOAD = 100_000;

export interface AdvancedUiValues {
  populationSize: number;
  baseK: number;
  maxChats: number;
  initiatorPercent: number;
  weakTiePercent: number;
  minutesPerRound: number;
}

export interface EffectiveSimulationConfig {
  populationSize: number;
  baseK: number;
  maxChats: number;
  initiatorRate: number;
  weakTieRate: number;
  minutesPerRound: number;
}

export const SIMULATION_PRESETS: Record<PopulationMode, EffectiveSimulationConfig> = {
  small: {
    populationSize: 250,
    baseK: 10,
    maxChats: 2,
    initiatorRate: 0.20,
    weakTieRate: 0.05,
    minutesPerRound: 5,
  },
  standard: {
    populationSize: 1_000,
    baseK: 14,
    maxChats: 2,
    initiatorRate: 0.20,
    weakTieRate: 0.05,
    minutesPerRound: 5,
  },
  large: {
    populationSize: 5_000,
    baseK: 18,
    maxChats: 2,
    initiatorRate: 0.20,
    weakTieRate: 0.05,
    minutesPerRound: 5,
  },
};

export function advancedValuesFromPreset(mode: PopulationMode): AdvancedUiValues {
  const preset = SIMULATION_PRESETS[mode];
  return {
    populationSize: preset.populationSize,
    baseK: preset.baseK,
    maxChats: preset.maxChats,
    initiatorPercent: preset.initiatorRate * 100,
    weakTiePercent: preset.weakTieRate * 100,
    minutesPerRound: preset.minutesPerRound,
  };
}

export function buildAdvancedConfig(values: AdvancedUiValues): AdvancedSimulationConfig {
  return {
    population_size: values.populationSize,
    base_k: values.baseK,
    max_conversations_per_round: values.maxChats,
    initiator_rate: values.initiatorPercent / 100,
    weak_tie_rate: values.weakTiePercent / 100,
    simulated_minutes_per_round: values.minutesPerRound,
  };
}

export function effectiveSimulationConfig({
  advancedEnabled,
  populationMode,
  advancedValues,
}: {
  advancedEnabled: boolean;
  populationMode: PopulationMode;
  advancedValues: AdvancedUiValues;
}): EffectiveSimulationConfig {
  if (!advancedEnabled) {
    return SIMULATION_PRESETS[populationMode];
  }
  return {
    populationSize: advancedValues.populationSize,
    baseK: advancedValues.baseK,
    maxChats: advancedValues.maxChats,
    initiatorRate: advancedValues.initiatorPercent / 100,
    weakTieRate: advancedValues.weakTiePercent / 100,
    minutesPerRound: advancedValues.minutesPerRound,
  };
}

export function conversationUpperBound(
  config: EffectiveSimulationConfig,
  rounds: number,
): number {
  return Math.floor((config.populationSize * config.maxChats) / 2) * rounds;
}

export function validateAdvancedSimulationConfig(
  values: AdvancedUiValues,
  rounds: number,
): string | null {
  if (!Number.isInteger(values.populationSize) || values.populationSize < 2 || values.populationSize > 5_000) {
    return "Population must be a whole number between 2 and 5,000 agents.";
  }
  if (!Number.isInteger(values.baseK) || values.baseK < 1 || values.baseK > 128) {
    return "K neighbors must be a whole number between 1 and 128.";
  }
  if (values.baseK >= values.populationSize) {
    return "K neighbors must be less than population size.";
  }
  if (!Number.isInteger(values.maxChats) || values.maxChats < 1 || values.maxChats > 8) {
    return "Max chats per agent per round must be a whole number between 1 and 8.";
  }
  if (!Number.isFinite(values.initiatorPercent) || values.initiatorPercent < 0 || values.initiatorPercent > 100) {
    return "Potential initiators must be between 0% and 100%.";
  }
  if (!Number.isFinite(values.weakTiePercent) || values.weakTiePercent < 0 || values.weakTiePercent > 100) {
    return "Weak social ties must be between 0% and 100%.";
  }
  if (!Number.isInteger(values.minutesPerRound) || values.minutesPerRound < 1 || values.minutesPerRound > 1_440) {
    return "Minutes per round must be a whole number between 1 and 1,440.";
  }
  if (!Number.isInteger(rounds) || rounds < 1 || rounds > 100) {
    return "Simulation rounds must be a whole number between 1 and 100 in Advanced mode.";
  }

  const upperBound = conversationUpperBound(
    effectiveSimulationConfig({
      advancedEnabled: true,
      populationMode: "small",
      advancedValues: values,
    }),
    rounds,
  );
  if (upperBound > MAX_SIMULATION_WORKLOAD) {
    return `Conservative workload upper bound is ${upperBound.toLocaleString("en-US")} conversations; maximum allowed is ${MAX_SIMULATION_WORKLOAD.toLocaleString("en-US")}.`;
  }
  return null;
}
