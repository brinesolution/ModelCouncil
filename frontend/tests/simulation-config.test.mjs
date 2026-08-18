import assert from "node:assert/strict";
import test from "node:test";

import {
  MAX_SIMULATION_WORKLOAD,
  advancedValuesFromPreset,
  buildAdvancedConfig,
  conversationUpperBound,
  effectiveSimulationConfig,
  validateAdvancedSimulationConfig,
} from "../lib/simulation-config.ts";


test("advanced values initialize from registered preset defaults", () => {
  assert.deepEqual(advancedValuesFromPreset("standard"), {
    populationSize: 1000,
    baseK: 14,
    maxChats: 2,
    initiatorPercent: 20,
    weakTiePercent: 5,
    minutesPerRound: 5,
  });
});


test("advanced payload converts percentages to backend fractions without clamping", () => {
  assert.deepEqual(
    buildAdvancedConfig({
      populationSize: 40,
      baseK: 6,
      maxChats: 1,
      initiatorPercent: 15,
      weakTiePercent: 8,
      minutesPerRound: 2,
    }),
    {
      population_size: 40,
      base_k: 6,
      max_conversations_per_round: 1,
      initiator_rate: 0.15,
      weak_tie_rate: 0.08,
      simulated_minutes_per_round: 2,
    },
  );
});


test("effective config uses preset when advanced is off and custom values when on", () => {
  const custom = {
    populationSize: 40,
    baseK: 6,
    maxChats: 1,
    initiatorPercent: 15,
    weakTiePercent: 8,
    minutesPerRound: 2,
  };

  assert.deepEqual(
    effectiveSimulationConfig({
      advancedEnabled: false,
      populationMode: "small",
      advancedValues: custom,
    }),
    {
      populationSize: 250,
      baseK: 10,
      maxChats: 2,
      initiatorRate: 0.2,
      weakTieRate: 0.05,
      minutesPerRound: 5,
    },
  );
  assert.deepEqual(
    effectiveSimulationConfig({
      advancedEnabled: true,
      populationMode: "small",
      advancedValues: custom,
    }),
    {
      populationSize: 40,
      baseK: 6,
      maxChats: 1,
      initiatorRate: 0.15,
      weakTieRate: 0.08,
      minutesPerRound: 2,
    },
  );
});


test("conversation upper bound matches backend floor formula", () => {
  assert.equal(
    conversationUpperBound(
      {
        populationSize: 40,
        baseK: 6,
        maxChats: 1,
        initiatorRate: 0.2,
        weakTieRate: 0.05,
        minutesPerRound: 2,
      },
      3,
    ),
    60,
  );
});


test("advanced validation rejects invalid K and excessive workload", () => {
  const base = {
    populationSize: 20,
    baseK: 4,
    maxChats: 1,
    initiatorPercent: 20,
    weakTiePercent: 5,
    minutesPerRound: 2,
  };

  assert.match(
    validateAdvancedSimulationConfig({ ...base, baseK: 20 }, 2) ?? "",
    /K.*less than population/i,
  );
  assert.match(
    validateAdvancedSimulationConfig(
      {
        populationSize: 5000,
        baseK: 18,
        maxChats: 3,
        initiatorPercent: 20,
        weakTiePercent: 5,
        minutesPerRound: 5,
      },
      14,
    ) ?? "",
    /105,000.*100,000/i,
  );
  assert.equal(MAX_SIMULATION_WORKLOAD, 100_000);
});


test("valid fast-debug configuration has no validation error", () => {
  assert.equal(
    validateAdvancedSimulationConfig(
      {
        populationSize: 20,
        baseK: 4,
        maxChats: 1,
        initiatorPercent: 15,
        weakTiePercent: 5,
        minutesPerRound: 2,
      },
      3,
    ),
    null,
  );
});
