import { ChartFrame } from "@/features/analytics/chart-frame";
import { percent, svgPoint } from "@/features/analytics/chart-utils";
import type { SimulationTimelinePoint } from "@/types/results";

interface TrendLinesProps {
  timeline: SimulationTimelinePoint[];
}

const WIDTH = 360;
const HEIGHT = 200;
const PAD_X = 34;
const PAD_Y = 28;

function points(timeline: SimulationTimelinePoint[], accessor: (point: SimulationTimelinePoint) => number) {
  return timeline
    .map((point, index) => {
      const { x, y } = svgPoint(index, timeline.length, accessor(point), WIDTH, HEIGHT, PAD_X, PAD_Y);
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
}

export function TrendLines({ timeline }: TrendLinesProps) {
  const opinionPoints = points(timeline, (point) => (point.mean_opinion + 1) / 2);
  const purchasePoints = points(timeline, (point) => point.mean_purchase_intent);
  const final = timeline[timeline.length - 1];

  return (
    <ChartFrame
      number="03"
      title="Opinion + purchase trend"
      description="Mean state movement across synchronous rounds."
      footer={
        <div className="chartLegendGrid chartLegendTwo">
          <span><i className="legendLine legendOpinion" />Opinion <strong>{final.mean_opinion.toFixed(2)}</strong></span>
          <span><i className="legendLine legendPurchase" />Purchase <strong>{percent(final.mean_purchase_intent)}</strong></span>
        </div>
      }
    >
      <svg className="analyticsSvg" viewBox={`0 0 ${WIDTH} ${HEIGHT}`} role="img" aria-label="Mean opinion and purchase intent across simulation rounds">
        {[0.25, 0.5, 0.75].map((fraction) => (
          <line
            key={fraction}
            x1={PAD_X}
            x2={WIDTH - PAD_X}
            y1={PAD_Y + (1 - fraction) * (HEIGHT - PAD_Y * 2)}
            y2={PAD_Y + (1 - fraction) * (HEIGHT - PAD_Y * 2)}
            className="chartGridLine"
          />
        ))}
        <line x1={PAD_X} x2={WIDTH - PAD_X} y1={HEIGHT - PAD_Y} y2={HEIGHT - PAD_Y} className="chartAxis" />
        <polyline points={opinionPoints} className="trendOpinion" />
        <polyline points={purchasePoints} className="trendPurchase" />
        <text x={PAD_X} y={HEIGHT - 8} className="chartLabel">R0</text>
        <text x={WIDTH - PAD_X} y={HEIGHT - 8} textAnchor="end" className="chartLabel">R{timeline.length - 1}</text>
      </svg>
    </ChartFrame>
  );
}
