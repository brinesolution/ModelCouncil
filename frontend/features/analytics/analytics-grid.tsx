import { ConversationVolume } from "@/features/analytics/conversation-volume";
import { InfluenceScatter } from "@/features/analytics/influence-scatter";
import { PurchaseBars } from "@/features/analytics/purchase-bars";
import { SentimentDonut } from "@/features/analytics/sentiment-donut";
import { TopicPressure } from "@/features/analytics/topic-pressure";
import { TrendLines } from "@/features/analytics/trend-lines";
import type { SimulationRunResponse } from "@/types/results";

interface AnalyticsGridProps {
  result: SimulationRunResponse;
}

export function AnalyticsGrid({ result }: AnalyticsGridProps) {
  const finalPoint = result.timeline[result.timeline.length - 1];

  return (
    <section className="analyticsSection" aria-labelledby="analytics-title">
      <header className="analyticsSectionHeader">
        <div>
          <span className="techLabel">Analytics matrix / six semantic views</span>
          <h2 id="analytics-title">Consumer response instrumentation</h2>
          <p>
            Six complementary views of final state, round dynamics, conversation pressure, and influential agents.
          </p>
        </div>
        <span className="analyticsRunId mono">SEED {result.seed} / R{result.rounds}</span>
      </header>
      <div className="analyticsGrid">
        <SentimentDonut finalPoint={finalPoint} />
        <PurchaseBars distribution={result.analytics.purchase_intent_distribution} />
        <TrendLines timeline={result.timeline} />
        <ConversationVolume timeline={result.timeline} />
        <TopicPressure points={result.analytics.topic_pressure} />
        <InfluenceScatter nodes={result.network.nodes} />
      </div>
    </section>
  );
}
