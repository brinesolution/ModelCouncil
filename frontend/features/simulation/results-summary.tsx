import type { SimulationRunResponse } from "@/types/results";

interface ResultsSummaryProps {
  result: SimulationRunResponse;
}

function percent(value: number) {
  return `${Math.round(value * 100)}%`;
}

export function ResultsSummary({ result }: ResultsSummaryProps) {
  const finalPoint = result.timeline[result.timeline.length - 1];

  return (
    <section className="resultSection" aria-labelledby="results-summary-title">
      <div className="resultHeader">
        <div>
          <p className="eyebrow">Synthetic simulation</p>
          <h2 id="results-summary-title">{result.product_name}</h2>
        </div>
        <span className="muted">Traits: {result.trait_source}</span>
      </div>

      <div className="summaryGrid">
        <div className="summaryMetric"><span>Population</span><strong>{result.summary.population_size.toLocaleString()}</strong></div>
        <div className="summaryMetric"><span>Conversations</span><strong>{result.summary.conversation_count.toLocaleString()}</strong></div>
        <div className="summaryMetric"><span>Purchase intent</span><strong>{percent(result.summary.final_mean_purchase_intent)}</strong></div>
        <div className="summaryMetric"><span>Positive share</span><strong>{percent(finalPoint.positive_share)}</strong></div>
        <div className="summaryMetric"><span>Neutral share</span><strong>{percent(finalPoint.neutral_share)}</strong></div>
        <div className="summaryMetric"><span>Negative share</span><strong>{percent(finalPoint.negative_share)}</strong></div>
      </div>

      <p className="muted resultDisclaimer">
        These values describe the configured synthetic population and simulation assumptions; they are not a real-market survey estimate.
      </p>
    </section>
  );
}
