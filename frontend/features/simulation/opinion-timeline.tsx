import type { SimulationTimelinePoint } from "@/types/results";

interface OpinionTimelineProps {
  timeline: SimulationTimelinePoint[];
}

const WIDTH = 760;
const HEIGHT = 260;
const PAD = 36;

function polyline(
  timeline: SimulationTimelinePoint[],
  value: (point: SimulationTimelinePoint) => number,
) {
  const maxIndex = Math.max(1, timeline.length - 1);
  return timeline
    .map((point, index) => {
      const x = PAD + (index / maxIndex) * (WIDTH - PAD * 2);
      const y = PAD + (1 - value(point)) * (HEIGHT - PAD * 2);
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
}

export function OpinionTimeline({ timeline }: OpinionTimelineProps) {
  const opinionPoints = polyline(timeline, (point) => (point.mean_opinion + 1) / 2);
  const purchasePoints = polyline(timeline, (point) => point.mean_purchase_intent);

  return (
    <section className="resultSection" aria-labelledby="timeline-title">
      <div className="resultHeader">
        <div>
          <h2 id="timeline-title">Opinion evolution</h2>
          <p className="muted">Mean population state after each synchronous round.</p>
        </div>
        <div className="chartLegend" aria-label="Chart legend">
          <span><i className="legendLine opinionLine" />Opinion</span>
          <span><i className="legendLine purchaseLine" />Purchase intent</span>
        </div>
      </div>

      <div className="chartFrame">
        <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} role="img" aria-label="Opinion and purchase intent timeline">
          <line x1={PAD} x2={WIDTH - PAD} y1={HEIGHT / 2} y2={HEIGHT / 2} className="chartAxis" />
          <line x1={PAD} x2={PAD} y1={PAD} y2={HEIGHT - PAD} className="chartAxis" />
          <line x1={PAD} x2={WIDTH - PAD} y1={HEIGHT - PAD} y2={HEIGHT - PAD} className="chartAxis" />
          <polyline points={opinionPoints} className="timelineOpinion" />
          <polyline points={purchasePoints} className="timelinePurchase" />
          <text x={PAD} y={HEIGHT - 8} className="chartLabel">Round 0</text>
          <text x={WIDTH - PAD} y={HEIGHT - 8} textAnchor="end" className="chartLabel">Round {timeline.length - 1}</text>
          <text x={8} y={PAD + 4} className="chartLabel">High</text>
          <text x={8} y={HEIGHT - PAD} className="chartLabel">Low</text>
        </svg>
      </div>
    </section>
  );
}
