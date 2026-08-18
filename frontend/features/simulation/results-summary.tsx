import { LedStatus } from "@/components/industrial/led-status";
import { PanelDetails } from "@/components/industrial/panel-details";
import type { SimulationRunResponse } from "@/types/results";

interface ResultsSummaryProps {
  result: SimulationRunResponse;
}

function percent(value: number) {
  return `${Math.round(value * 100)}%`;
}

function milliseconds(value: number) {
  return value > 0 ? `${Math.round(value)} ms` : "—";
}

function estimatedCost(value: number) {
  return `$${value.toFixed(value < 0.01 ? 6 : 4)}`;
}

export function ResultsSummary({ result }: ResultsSummaryProps) {
  const finalPoint = result.timeline[result.timeline.length - 1];
  const providerLive = result.dialogue_stats.provider_available;
  const localProvider = result.llm_provider === "ollama";
  const providerLabel = result.llm_provider === "ollama"
    ? "Ollama Local"
    : result.llm_provider === "deepseek"
      ? "DeepSeek"
      : null;

  return (
    <section className="resultSection executiveModule" aria-labelledby="results-summary-title">
      <PanelDetails />
      <div className="executiveHeader">
        <div>
          <span className="techLabel">Executive output / synthetic simulation</span>
          <h1 id="results-summary-title">{result.product_name}</h1>
          <p>
            Final population state after {result.rounds} synchronous rounds {result.advanced_config_enabled
              ? `using Advanced overrides based on the ${result.population_mode} preset.`
              : `using the ${result.population_mode} preset.`}
          </p>
        </div>
        <div className="executiveStatus">
          <LedStatus label={providerLive ? "Live dialogue" : "Deterministic dialogue"} tone={providerLive ? "red" : "green"} />
          <span className="mono muted">TRAITS/{result.trait_source.toUpperCase()}</span>
        </div>
      </div>

      <div className="summaryGrid">
        <div className="summaryMetric"><span>Configuration</span><strong>{result.advanced_config_enabled ? "ADVANCED" : "PRESET"}</strong></div>
        <div className="summaryMetric"><span>Population</span><strong>{result.summary.population_size.toLocaleString()}</strong></div>
        <div className="summaryMetric"><span>Conversations</span><strong>{result.summary.conversation_count.toLocaleString()}</strong></div>
        <div className="summaryMetric"><span>Billing cadence</span><strong>{result.billing_cadence.replace("_", " ")}</strong></div>
        <div className="summaryMetric"><span>Purchase intent</span><strong>{percent(result.summary.final_mean_purchase_intent)}</strong></div>
        <div className="summaryMetric"><span>Mean opinion</span><strong>{result.summary.final_mean_opinion.toFixed(2)}</strong></div>
        <div className="summaryMetric"><span>Positive</span><strong>{percent(finalPoint.positive_share)}</strong></div>
        <div className="summaryMetric"><span>Neutral</span><strong>{percent(finalPoint.neutral_share)}</strong></div>
        <div className="summaryMetric"><span>Negative</span><strong>{percent(finalPoint.negative_share)}</strong></div>
        <div className="summaryMetric"><span>K neighbors</span><strong>{result.preset.base_k}</strong></div>
        <div className="summaryMetric"><span>Max chats / agent / round</span><strong>{result.preset.max_conversations_per_round}</strong></div>
        <div className="summaryMetric"><span>Live rendered</span><strong>{result.dialogue_stats.llm_rendered.toLocaleString()}</strong></div>
      </div>

      <div className="dialogueTelemetry" aria-label="Live dialogue telemetry">
        <div className="dialogueTelemetryHeader">
          <div>
            <span className="techLabel">Language subsystem / provider telemetry</span>
            <h2>{result.llm_model ?? result.dialogue_stats.provider_model ?? "Deterministic fallback"}</h2>
          </div>
          <LedStatus
            label={providerLive ? "Provider enabled" : "Provider offline"}
            tone={providerLive ? "red" : "green"}
            compact
          />
        </div>
        <div className="telemetryGrid">
          <div><span>Selected / rendered</span><strong>{result.dialogue_stats.selected_for_llm} / {result.dialogue_stats.llm_rendered}</strong></div>
          <div><span>Fallbacks</span><strong>{result.dialogue_stats.fallback_count}</strong></div>
          <div><span>Provider</span><strong>{providerLabel ?? result.dialogue_stats.provider_model ?? "Deterministic"}</strong></div>
          <div><span>Cache hit ratio</span><strong>{localProvider ? "N/A" : percent(result.dialogue_stats.cache_hit_ratio)}</strong></div>
          <div><span>Cache hit tokens</span><strong>{localProvider ? "N/A" : result.dialogue_stats.prompt_cache_hit_tokens.toLocaleString()}</strong></div>
          <div><span>Input tokens</span><strong>{result.dialogue_stats.prompt_tokens.toLocaleString()}</strong></div>
          <div><span>Output tokens</span><strong>{result.dialogue_stats.completion_tokens.toLocaleString()}</strong></div>
          <div><span>Avg / max latency</span><strong>{milliseconds(result.dialogue_stats.average_latency_ms)} / {milliseconds(result.dialogue_stats.max_latency_ms)}</strong></div>
          <div><span>{localProvider ? "Billing" : "Estimated API cost"}</span><strong>{localProvider ? "Local compute" : estimatedCost(result.dialogue_stats.estimated_cost_usd)}</strong></div>
        </div>
        <p className="telemetryNote">
          Provider telemetry describes transcript rendering only. Numerical consumer state remains deterministic and was committed before language rendering.
        </p>
      </div>

      <p className="resultDisclaimer">
        Synthetic experiment output—not a statistically validated real-market survey estimate.
      </p>
    </section>
  );
}
