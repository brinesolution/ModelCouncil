import assert from "node:assert/strict";
import test from "node:test";

import {
  DEFAULT_PRODUCT_PRESET_ID,
  PRODUCT_PRESETS,
} from "../lib/product-presets.ts";


test("product preset catalog contains five substantial non-gym scenarios", () => {
  assert.equal(PRODUCT_PRESETS.length, 5);
  assert.equal(new Set(PRODUCT_PRESETS.map((preset) => preset.id)).size, 5);
  assert.ok(PRODUCT_PRESETS.some((preset) => preset.id === DEFAULT_PRODUCT_PRESET_ID));

  for (const preset of PRODUCT_PRESETS) {
    assert.ok(preset.name.trim().length >= 3);
    assert.ok(preset.category.trim().length >= 3);
    assert.ok(preset.pitch.length >= 800, `${preset.id} pitch should be detailed`);
    assert.ok(Number.isFinite(preset.price));
    assert.ok(preset.price >= 0);
    assert.ok(["one_time", "monthly", "yearly"].includes(preset.billingCadence));
    assert.ok(preset.scenarioLabel.trim().length >= 3);
    assert.doesNotMatch(`${preset.name} ${preset.category} ${preset.pitch}`.toLowerCase(), /gym subscription|ai fitness coach/);
  }
});


test("preset catalog spans product forms and includes a deliberate stress-test scenario", () => {
  assert.ok(new Set(PRODUCT_PRESETS.map((preset) => preset.category)).size >= 4);
  assert.ok(PRODUCT_PRESETS.some((preset) => preset.scenarioTone === "stress_test"));
  assert.ok(PRODUCT_PRESETS.some((preset) => preset.scenarioTone === "favorable"));
  assert.ok(PRODUCT_PRESETS.some((preset) => preset.scenarioTone === "mixed"));
});
