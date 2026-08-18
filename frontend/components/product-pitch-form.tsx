"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

import { FullLiveConfirmationDialog } from "@/components/full-live-confirmation-dialog";
import { FullLiveProviderSelector } from "@/components/full-live-provider-selector";
import { LedStatus } from "@/components/industrial/led-status";
import { PanelDetails } from "@/components/industrial/panel-details";
import { runSimulation, startFullLiveSimulation } from "@/lib/api";
import {
  MAX_SIMULATION_WORKLOAD,
  advancedValuesFromPreset,
  buildAdvancedConfig,
  conversationUpperBound,
  effectiveSimulationConfig,
  validateAdvancedSimulationConfig,
  type AdvancedUiValues,
} from "@/lib/simulation-config";
import type { LlmSelection } from "@/types/llm-provider";
import {
  WEB_ROUND_LIMITS,
  type BillingCadence,
  type DialogueMode,
  type PopulationMode,
} from "@/types/simulation";

const DEFAULT_PITCH =
  "An AI-powered fitness coach that creates personalized workout plans, nutrition guidance, and progress tracking for one monthly subscription.";

function billingAutoHint(pitch: string, category: string): string {
  const text = `${category} ${pitch}`.toLowerCase();
  if (/no subscription|no recurring fee|one[- ]time|lifetime purchase/.test(text)) return "One-time";
  if (/\/\s*month|per month|monthly|billed monthly/.test(text)) return "Monthly";
  if (/\/\s*year|per year|yearly|annual|billed annually/.test(text)) return "Yearly";
  if (/software|saas|service|platform|app|ai coach|digital coach/.test(text)) return "Monthly";
  return "One-time";
}

function formatPercent(rate: number): string {
  const value = rate * 100;
  return `${Number.isInteger(value) ? value.toFixed(0) : value.toFixed(1)}%`;
}

const DIALOGUE_DESCRIPTIONS: Record<DialogueMode, string> = {
  economy: "Top ~5% by importance, with a policy cap of 6 live renders.",
  balanced: "Top ~20% by importance; the server live-request budget may cap this lower.",
  full: "All eligible conversations, still constrained by the normal live-request safety budget.",
  full_live: "Every scheduled conversation is rendered by the selected language model. No total-call cap.",
};

export function ProductPitchForm() {
  const router = useRouter();
  const [name, setName] = useState("AI Fitness Coach");
  const [category, setCategory] = useState("Fitness Technology");
  const [pitch, setPitch] = useState(DEFAULT_PITCH);
  const [price, setPrice] = useState("999");
  const [billingCadence, setBillingCadence] = useState<BillingCadence>("auto");
  const [populationMode, setPopulationMode] = useState<PopulationMode>("standard");
  const [dialogueMode, setDialogueMode] = useState<DialogueMode>("balanced");
  const [rounds, setRounds] = useState(20);
  const [seed, setSeed] = useState(42);
  const [advancedEnabled, setAdvancedEnabled] = useState(false);
  const [advancedValues, setAdvancedValues] = useState<AdvancedUiValues>(() =>
    advancedValuesFromPreset("standard"),
  );
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [showFullLiveConfirmation, setShowFullLiveConfirmation] = useState(false);
  const [fullLiveSelection, setFullLiveSelection] = useState<LlmSelection | null>(null);

  const effectiveConfig = effectiveSimulationConfig({
    advancedEnabled,
    populationMode,
    advancedValues,
  });
  const roundLimit = advancedEnabled ? 100 : WEB_ROUND_LIMITS[populationMode];
  const workloadUpperBound = conversationUpperBound(effectiveConfig, rounds);
  const fullLiveUpperBound = workloadUpperBound;
  const advancedValidationError = advancedEnabled
    ? validateAdvancedSimulationConfig(advancedValues, rounds)
    : null;
  const visibleError = error ?? advancedValidationError;
  const runDisabled = Boolean(
    loading
      || advancedValidationError
      || (dialogueMode === "full_live" && !fullLiveSelection),
  );

  function handlePopulationChange(nextMode: PopulationMode) {
    setPopulationMode(nextMode);
    setError(null);
    if (advancedEnabled) {
      setAdvancedValues(advancedValuesFromPreset(nextMode));
      return;
    }
    setRounds((current) => Math.min(current, WEB_ROUND_LIMITS[nextMode]));
  }

  function handleAdvancedToggle(nextEnabled: boolean) {
    setError(null);
    setShowFullLiveConfirmation(false);
    if (nextEnabled) {
      setAdvancedValues(advancedValuesFromPreset(populationMode));
      setAdvancedEnabled(true);
      return;
    }
    setAdvancedEnabled(false);
    setAdvancedValues(advancedValuesFromPreset(populationMode));
    setRounds((current) => Math.min(Math.max(current, 1), WEB_ROUND_LIMITS[populationMode]));
  }

  function updateAdvancedValue<K extends keyof AdvancedUiValues>(
    key: K,
    value: AdvancedUiValues[K],
  ) {
    setError(null);
    setAdvancedValues((current) => ({ ...current, [key]: value }));
  }

  function handleRoundsChange(nextValue: number) {
    setError(null);
    if (advancedEnabled) {
      setRounds(nextValue);
      return;
    }
    setRounds(Math.min(Math.max(nextValue, 1), WEB_ROUND_LIMITS[populationMode]));
  }

  function handleDialogueModeChange(nextMode: DialogueMode) {
    setDialogueMode(nextMode);
    if (nextMode !== "full_live") {
      setFullLiveSelection(null);
      setShowFullLiveConfirmation(false);
    }
  }

  function productPayload() {
    return {
      name,
      category,
      pitch,
      price: price.trim() === "" ? null : Number(price),
      currency: "INR",
      billing_cadence: billingCadence,
    };
  }

  function advancedRequestFields() {
    return advancedEnabled
      ? { advanced_config: buildAdvancedConfig(advancedValues) }
      : {};
  }

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    if (advancedValidationError) {
      return;
    }

    if (dialogueMode === "full_live") {
      if (!fullLiveSelection) {
        setError("Select an available Full Live language source and model before starting.");
        return;
      }
      setShowFullLiveConfirmation(true);
      return;
    }

    setLoading(true);
    try {
      const data = await runSimulation({
        product: productPayload(),
        population_mode: populationMode,
        dialogue_mode: dialogueMode,
        rounds,
        seed,
        ...advancedRequestFields(),
      });
      window.sessionStorage.setItem(
        "modelcouncil:last-simulation",
        JSON.stringify(data),
      );
      router.push("/simulations/result");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to reach ModelCouncil API.");
    } finally {
      setLoading(false);
    }
  }

  async function startConfirmedFullLive() {
    if (advancedValidationError) {
      setShowFullLiveConfirmation(false);
      return;
    }
    if (!fullLiveSelection) {
      setShowFullLiveConfirmation(false);
      setError("The selected Full Live provider/model is no longer available. Refresh providers and choose again.");
      return;
    }
    setShowFullLiveConfirmation(false);
    setError(null);
    setLoading(true);
    try {
      const job = await startFullLiveSimulation({
        product: productPayload(),
        population_mode: populationMode,
        dialogue_mode: "full_live",
        rounds,
        seed,
        ...advancedRequestFields(),
        full_live_confirmed: true,
        llm_provider: fullLiveSelection.provider.id,
        llm_model: fullLiveSelection.model.id,
      });
      router.push(`/simulations/full-live/${job.job_id}`);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to start Full Live simulation.");
      setLoading(false);
    }
  }

  return (
    <div className="simLayout">
      <form className="formPanel" onSubmit={onSubmit}>
        <PanelDetails />
        <div className="formPanelHeader">
          <div>
            <span className="techLabel">Input module / MC-PITCH-01</span>
            <h2>Product information</h2>
          </div>
          <LedStatus label={loading ? "Running" : "Ready"} tone={loading ? "red" : "green"} compact />
        </div>

        <div className="formGrid">
          <div className="field">
            <label htmlFor="product-name">Product name</label>
            <input id="product-name" value={name} onChange={(event) => setName(event.target.value)} required />
          </div>

          <div className="field">
            <label htmlFor="category">Category</label>
            <input id="category" value={category} onChange={(event) => setCategory(event.target.value)} />
          </div>

          <div className="field">
            <label htmlFor="price">Price / INR</label>
            <input id="price" type="number" min="0" step="0.01" value={price} onChange={(event) => setPrice(event.target.value)} />
          </div>

          {price.trim() !== "" ? (
            <div className="field">
              <label htmlFor="billing-cadence">Billing cadence</label>
              <select
                id="billing-cadence"
                value={billingCadence}
                onChange={(event) => setBillingCadence(event.target.value as BillingCadence)}
              >
                <option value="auto">Auto</option>
                <option value="one_time">One-time</option>
                <option value="monthly">Monthly</option>
                <option value="yearly">Yearly</option>
              </select>
              <span className="muted">
                {billingCadence === "auto"
                  ? `Auto — likely ${billingAutoHint(pitch, category)}. Backend resolution is authoritative.`
                  : `Manual override — ${billingCadence.replace("_", " ")}.`}
              </span>
            </div>
          ) : null}

          <div className="field full">
            <label htmlFor="pitch">Product pitch</label>
            <textarea id="pitch" value={pitch} onChange={(event) => setPitch(event.target.value)} minLength={10} required />
            <span className="muted mono">{pitch.length.toLocaleString()} / 12,000 characters</span>
          </div>

          <div className="field">
            <label htmlFor="population">Population preset</label>
            <select
              id="population"
              value={populationMode}
              onChange={(event) => handlePopulationChange(event.target.value as PopulationMode)}
            >
              <option value="small">Small — 250 agents</option>
              <option value="standard">Standard — 1,000 agents</option>
              <option value="large">Large — 5,000 agents</option>
            </select>
            <span className="muted">Acts as the baseline template when Advanced controls are enabled.</span>
          </div>

          <div className="field">
            <label htmlFor="dialogue">Dialogue mode</label>
            <select id="dialogue" value={dialogueMode} onChange={(event) => handleDialogueModeChange(event.target.value as DialogueMode)}>
              <option value="economy">Economy</option>
              <option value="balanced">Balanced</option>
              <option value="full">Full dialogue</option>
              <option value="full_live">Full Live — every scheduled conversation</option>
            </select>
            <span className="muted">{DIALOGUE_DESCRIPTIONS[dialogueMode]}</span>
            {dialogueMode === "full_live" ? (
              <div className="fullLiveInlineWarning" role="status">
                <strong>Uncapped Full Live mode.</strong> Every scheduled conversation will be rendered by the selected model after the deterministic simulation. Current conservative upper bound: <span className="mono">{fullLiveUpperBound.toLocaleString()} calls</span>.
              </div>
            ) : null}
          </div>

          {dialogueMode === "full_live" ? (
            <FullLiveProviderSelector onSelectionChange={setFullLiveSelection} />
          ) : null}

          <div className={`advancedToggleModule ${advancedEnabled ? "isAdvanced" : ""}`}>
            <label className="advancedToggle" htmlFor="advanced-controls">
              <span className="advancedToggleControl">
                <input
                  id="advanced-controls"
                  type="checkbox"
                  checked={advancedEnabled}
                  onChange={(event) => handleAdvancedToggle(event.target.checked)}
                  aria-expanded={advancedEnabled}
                />
                <span className="advancedToggleTrack" aria-hidden="true"><span /></span>
              </span>
              <span className="advancedToggleCopy">
                <strong>Advanced simulation controls</strong>
                <small>Override numerical preset values for fast tests, provider debugging, and focused experiments. Dialogue mode remains independent.</small>
              </span>
              <span className="advancedModeBadge">{advancedEnabled ? "ADVANCED" : "PRESET"}</span>
            </label>
          </div>

          {advancedEnabled ? (
            <div className="advancedControlModule" aria-label="Advanced simulation controls">
              <div className="advancedControlHeader">
                <div>
                  <span className="techLabel">Override bank / MC-ADV-01</span>
                  <h3>Numerical runtime controls</h3>
                </div>
                <span className="advancedModeBadge active">CUSTOM ACTIVE</span>
              </div>
              <div className="advancedGrid">
                <div className="field">
                  <label htmlFor="advanced-population">Population agents</label>
                  <input id="advanced-population" type="number" min="2" max="5000" step="1" value={advancedValues.populationSize} onChange={(event) => updateAdvancedValue("populationSize", Number(event.target.value))} />
                  <span className="muted">2–5,000 agents.</span>
                </div>
                <div className="field">
                  <label htmlFor="advanced-k">K neighbors</label>
                  <input id="advanced-k" type="number" min="1" max="128" step="1" value={advancedValues.baseK} onChange={(event) => updateAdvancedValue("baseK", Number(event.target.value))} />
                  <span className="muted">1–128 and lower than population.</span>
                </div>
                <div className="field">
                  <label htmlFor="advanced-rounds">Simulation rounds</label>
                  <input id="advanced-rounds" type="number" min="1" max="100" step="1" value={rounds} onChange={(event) => handleRoundsChange(Number(event.target.value))} />
                  <span className="muted">1–100; workload guard remains active.</span>
                </div>
                <div className="field">
                  <label htmlFor="advanced-chats">Max chats / agent / round</label>
                  <input id="advanced-chats" type="number" min="1" max="8" step="1" value={advancedValues.maxChats} onChange={(event) => updateAdvancedValue("maxChats", Number(event.target.value))} />
                  <span className="muted">1–8 conversation capacity.</span>
                </div>
                <div className="field">
                  <label htmlFor="advanced-initiators">Potential initiators / %</label>
                  <input id="advanced-initiators" type="number" min="0" max="100" step="0.1" value={advancedValues.initiatorPercent} onChange={(event) => updateAdvancedValue("initiatorPercent", Number(event.target.value))} />
                  <span className="muted">0–100% of agents may initiate.</span>
                </div>
                <div className="field">
                  <label htmlFor="advanced-weak-ties">Weak social ties / %</label>
                  <input id="advanced-weak-ties" type="number" min="0" max="100" step="0.1" value={advancedValues.weakTiePercent} onChange={(event) => updateAdvancedValue("weakTiePercent", Number(event.target.value))} />
                  <span className="muted">0–100% additional weak-tie rate.</span>
                </div>
                <div className="field">
                  <label htmlFor="advanced-minutes">Minutes per round</label>
                  <input id="advanced-minutes" type="number" min="1" max="1440" step="1" value={advancedValues.minutesPerRound} onChange={(event) => updateAdvancedValue("minutesPerRound", Number(event.target.value))} />
                  <span className="muted">1–1,440 simulated minutes.</span>
                </div>
                <div className="field">
                  <label htmlFor="advanced-seed">Random seed</label>
                  <input id="advanced-seed" type="number" min="0" max="2147483647" step="1" value={seed} onChange={(event) => setSeed(Number(event.target.value))} />
                  <span className="muted">Shared with preset mode; preserves reproducibility.</span>
                </div>
              </div>
              <div className={`advancedWorkloadNote ${advancedValidationError ? "invalid" : ""}`} role={advancedValidationError ? "alert" : "status"}>
                <span>Conservative scheduled-conversation upper bound</span>
                <strong>{workloadUpperBound.toLocaleString()} / {MAX_SIMULATION_WORKLOAD.toLocaleString()}</strong>
                <small>{advancedValidationError ?? "Configuration is within the server workload guard."}</small>
              </div>
            </div>
          ) : (
            <>
              <div className="field">
                <label htmlFor="rounds">Simulation rounds</label>
                <input
                  id="rounds"
                  type="number"
                  min="1"
                  max={roundLimit}
                  value={rounds}
                  onChange={(event) => handleRoundsChange(Number(event.target.value))}
                />
                <span className="muted">Maximum for this population: {roundLimit} rounds.</span>
              </div>

              <div className="field">
                <label htmlFor="seed">Random seed</label>
                <input id="seed" type="number" min="0" max="2147483647" value={seed} onChange={(event) => setSeed(Number(event.target.value))} />
              </div>
            </>
          )}
        </div>

        <div className="formFooter">
          <span className={`status ${visibleError ? "error" : ""}`} role={visibleError ? "alert" : undefined}>
            {visibleError ?? (loading
              ? "Simulation is running. Semantic state is computed first; selected transcripts may be rendered afterward."
              : advancedEnabled
                ? "Advanced numerical overrides are active. Backend validation and the 100,000-conversation workload guard remain authoritative."
                : "Semantic state is deterministic. Live language rendering is a bounded server-side post-process.")}
          </span>
          <button
            className="button"
            type="submit"
            disabled={runDisabled}
          >
            {loading ? "Simulation running" : "Run simulation"}
          </button>
        </div>
      </form>

      <aside className="metricPanel">
        <PanelDetails />
        <div className="instrumentHeader">
          <div>
            <span className="techLabel">Run console / MC-CFG-02</span>
            <h2>Simulation parameters</h2>
          </div>
          <LedStatus label="Configured" tone="red" compact />
        </div>
        <div className="metricList">
          <div className="metric"><span>Configuration</span><strong>{advancedEnabled ? "ADVANCED" : "PRESET"}</strong></div>
          <div className="metric"><span>Population</span><strong>{effectiveConfig.populationSize.toLocaleString()} agents · K {effectiveConfig.baseK}</strong></div>
          <div className="metric"><span>Billing</span><strong>{price.trim() === "" ? "No price" : billingCadence === "auto" ? `Auto / ${billingAutoHint(pitch, category)}` : billingCadence.replace("_", " ")}</strong></div>
          <div className="metric"><span>Rounds</span><strong>{rounds}</strong></div>
          {advancedEnabled ? (
            <>
              <div className="metric"><span>Workload upper bound</span><strong>{workloadUpperBound.toLocaleString()} conv.</strong></div>
              <div className="metric"><span>Workload guard</span><strong>≤ {MAX_SIMULATION_WORKLOAD.toLocaleString()}</strong></div>
            </>
          ) : (
            <div className="metric"><span>Round limit</span><strong>{roundLimit}</strong></div>
          )}
          <div className="metric"><span>Simulated time</span><strong>{(rounds * effectiveConfig.minutesPerRound).toLocaleString()} min</strong></div>
          <div className="metric"><span>Max chats / agent / round</span><strong>{effectiveConfig.maxChats}</strong></div>
          <div className="metric"><span>Potential initiators</span><strong>{formatPercent(effectiveConfig.initiatorRate)}</strong></div>
          <div className="metric"><span>Weak social ties</span><strong>{formatPercent(effectiveConfig.weakTieRate)}</strong></div>
          <div className="metric"><span>Dialogue mode</span><strong>{dialogueMode}</strong></div>
          {dialogueMode === "full_live" ? (
            <div className="metric"><span>Language source</span><strong>{fullLiveSelection ? `${fullLiveSelection.provider.label} / ${fullLiveSelection.model.label}` : "Scanning…"}</strong></div>
          ) : null}
          <div className="metric"><span>Seed</span><strong>{seed}</strong></div>
        </div>
        <div className="instrumentNote">
          Every conversation is simulated semantically before any optional language rendering. Advanced changes numerical runtime configuration; Dialogue/source selection changes transcript wording coverage.
        </div>
      </aside>

      {showFullLiveConfirmation && fullLiveSelection ? (
        <FullLiveConfirmationDialog
          upperBoundCalls={fullLiveUpperBound}
          selection={fullLiveSelection}
          onCancel={() => setShowFullLiveConfirmation(false)}
          onConfirm={startConfirmedFullLive}
        />
      ) : null}
    </div>
  );
}
