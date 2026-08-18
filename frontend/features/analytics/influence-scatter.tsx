import { ChartFrame } from "@/features/analytics/chart-frame";
import type { SimulationNetworkNode } from "@/types/results";

interface InfluenceScatterProps {
  nodes: SimulationNetworkNode[];
}

const WIDTH = 360;
const HEIGHT = 200;
const PAD_X = 36;
const PAD_Y = 26;

function pointClass(opinion: number) {
  if (opinion > 0.2) return "scatterPositive";
  if (opinion < -0.2) return "scatterNegative";
  return "scatterNeutral";
}

export function InfluenceScatter({ nodes }: InfluenceScatterProps) {
  return (
    <ChartFrame
      number="06"
      title="Influence vs purchase intent"
      description="Sampled-agent map highlighting advocates, skeptics, and influential low-intent hubs."
      footer={<span className="chartFootnote mono">Sample: {nodes.length} visible agents</span>}
    >
      <svg className="analyticsSvg" viewBox={`0 0 ${WIDTH} ${HEIGHT}`} role="img" aria-label="Scatter plot of influence power versus purchase intent">
        {[0.25, 0.5, 0.75].map((fraction) => (
          <g key={fraction}>
            <line
              x1={PAD_X}
              x2={WIDTH - PAD_X}
              y1={PAD_Y + (1 - fraction) * (HEIGHT - PAD_Y * 2)}
              y2={PAD_Y + (1 - fraction) * (HEIGHT - PAD_Y * 2)}
              className="chartGridLine"
            />
            <line
              x1={PAD_X + fraction * (WIDTH - PAD_X * 2)}
              x2={PAD_X + fraction * (WIDTH - PAD_X * 2)}
              y1={PAD_Y}
              y2={HEIGHT - PAD_Y}
              className="chartGridLine"
            />
          </g>
        ))}
        <line x1={PAD_X} x2={WIDTH - PAD_X} y1={HEIGHT - PAD_Y} y2={HEIGHT - PAD_Y} className="chartAxis" />
        <line x1={PAD_X} x2={PAD_X} y1={PAD_Y} y2={HEIGHT - PAD_Y} className="chartAxis" />
        {nodes.map((node) => {
          const x = PAD_X + node.influence * (WIDTH - PAD_X * 2);
          const y = PAD_Y + (1 - node.purchase_intent) * (HEIGHT - PAD_Y * 2);
          return (
            <circle
              key={node.id}
              cx={x}
              cy={y}
              r={3.2 + node.influence * 1.8}
              className={`scatterPoint ${pointClass(node.opinion)}`}
            >
              <title>{`Agent ${node.id}: influence ${node.influence.toFixed(2)}, purchase ${(node.purchase_intent * 100).toFixed(0)}%, opinion ${node.opinion.toFixed(2)}`}</title>
            </circle>
          );
        })}
        <text x={WIDTH / 2} y={HEIGHT - 7} textAnchor="middle" className="chartLabel">INFLUENCE →</text>
        <text x="11" y="18" className="chartLabel">PURCHASE ↑</text>
      </svg>
    </ChartFrame>
  );
}
