import { ChartFrame } from "@/features/analytics/chart-frame";
import { percent } from "@/features/analytics/chart-utils";
import type { SimulationTimelinePoint } from "@/types/results";

interface SentimentDonutProps {
  finalPoint: SimulationTimelinePoint;
}

const RADIUS = 56;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

export function SentimentDonut({ finalPoint }: SentimentDonutProps) {
  const values = [
    { key: "positive", label: "Positive", value: finalPoint.positive_share, className: "donutPositive" },
    { key: "neutral", label: "Neutral", value: finalPoint.neutral_share, className: "donutNeutral" },
    { key: "negative", label: "Negative", value: finalPoint.negative_share, className: "donutNegative" },
  ] as const;

  let cumulative = 0;

  return (
    <ChartFrame
      number="01"
      title="Final sentiment composition"
      description="Population split after the final synchronous round."
      footer={
        <div className="chartLegendGrid">
          {values.map((item) => (
            <span key={item.key}>
              <i className={`legendDot ${item.className}`} />
              {item.label} <strong>{percent(item.value)}</strong>
            </span>
          ))}
        </div>
      }
    >
      <div className="donutLayout">
        <svg viewBox="0 0 170 170" role="img" aria-label="Final sentiment composition donut chart">
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
            {percent(finalPoint.positive_share)}
          </text>
          <text x="85" y="99" textAnchor="middle" className="donutCenterLabel">
            POSITIVE
          </text>
        </svg>
      </div>
    </ChartFrame>
  );
}
