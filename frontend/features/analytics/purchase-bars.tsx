import { ChartFrame } from "@/features/analytics/chart-frame";
import type { PurchaseIntentDistribution } from "@/types/results";

interface PurchaseBarsProps {
  distribution: PurchaseIntentDistribution;
}

export function PurchaseBars({ distribution }: PurchaseBarsProps) {
  const bars = [
    { label: "Low", value: distribution.low, className: "barLow" },
    { label: "Medium", value: distribution.medium, className: "barMedium" },
    { label: "High", value: distribution.high, className: "barHigh" },
  ];
  const maxValue = Math.max(1, ...bars.map((bar) => bar.value));
  const total = bars.reduce((sum, bar) => sum + bar.value, 0);

  return (
    <ChartFrame
      number="02"
      title="Purchase intent distribution"
      description="Full-population propensity bins: low, medium, and high."
      footer={<span className="chartFootnote mono">N={total.toLocaleString()} final agents</span>}
    >
      <svg className="analyticsSvg" viewBox="0 0 320 190" role="img" aria-label="Purchase intent distribution bar chart">
        <line x1="30" x2="300" y1="158" y2="158" className="chartAxis" />
        {bars.map((bar, index) => {
          const x = 58 + index * 84;
          const height = (bar.value / maxValue) * 112;
          return (
            <g key={bar.label}>
              <rect
                x={x}
                y={158 - height}
                width="46"
                height={height}
                rx="6"
                className={`purchaseBar ${bar.className}`}
              />
              <text x={x + 23} y={146 - height} textAnchor="middle" className="chartValue">
                {bar.value.toLocaleString()}
              </text>
              <text x={x + 23} y="177" textAnchor="middle" className="chartLabel">
                {bar.label}
              </text>
            </g>
          );
        })}
      </svg>
    </ChartFrame>
  );
}
