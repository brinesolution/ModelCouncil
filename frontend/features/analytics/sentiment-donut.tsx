import { ChartFrame } from "@/features/analytics/chart-frame";
import { percent } from "@/features/analytics/chart-utils";
import type { OpinionDiagnostics, SimulationTimelinePoint } from "@/types/results";

interface SentimentDonutProps {
  finalPoint: SimulationTimelinePoint;
  diagnostics: OpinionDiagnostics;
}

const RADIUS = 56;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

function signed(value: number): string {
  return `${value >= 0 ? "+" : ""}${value.toFixed(2)}`;
}

export function SentimentDonut({ finalPoint, diagnostics }: SentimentDonutProps) {
  const values = [
    { key: "positive", label: "Strong +", value: finalPoint.positive_share, className: "donutPositive" },
    { key: "neutral", label: "Middle band", value: finalPoint.neutral_share, className: "donutNeutral" },
    { key: "negative", label: "Strong −", value: finalPoint.negative_share, className: "donutNegative" },
  ] as const;

  let cumulative = 0;

  return (
    <ChartFrame
      number="01"
      title="Final opinion composition"
      description="Strong buckets use ±0.20. The diagnostic below also exposes every consumer whose continuous opinion is below zero."
      footer={
        <div className="sentimentFooter">
          <div className="chartLegendGrid">
            {values.map((item) => (
              <span key={item.key}>
                <i className={`legendDot ${item.className}`} />
                {item.label} <strong>{percent(item.value)}</strong>
              </span>
            ))}
          </div>
          <div className="sentimentDiagnostic" aria-label="Continuous opinion diagnostics">
            <span>Below zero <strong>{percent(diagnostics.below_zero_share)}</strong></span>
            <span>Min <strong>{signed(diagnostics.minimum)}</strong></span>
            <span>Median <strong>{signed(diagnostics.median)}</strong></span>
            <span>Strong-negative cutoff <strong>{signed(diagnostics.strong_negative_threshold)}</strong></span>
          </div>
        </div>
      }
    >
      <div className="donutLayout">
        <svg viewBox="0 0 170 170" role="img" aria-label="Final opinion composition donut chart">
          <circle className="donutTrack" cx="85" cy="85" r={RADIUS} />
          {values.map((item) => {
            const start = cumulative;
            cumulative += item.value;
            return (
              <circle
                key={item.key}
                className={`donutSegment ${item.className}`}
                cx="85"
                cy="85"
                r={RADIUS}
                strokeDasharray={`${item.value * CIRCUMFERENCE} ${CIRCUMFERENCE}`}
                strokeDashoffset={-start * CIRCUMFERENCE}
                transform="rotate(-90 85 85)"
              />
            );
          })}
          <text x="85" y="79" textAnchor="middle" className="donutCenterValue">
            {percent(diagnostics.below_zero_share)}
          </text>
          <text x="85" y="99" textAnchor="middle" className="donutCenterLabel">
            BELOW ZERO
          </text>
        </svg>
      </div>
    </ChartFrame>
  );
}
