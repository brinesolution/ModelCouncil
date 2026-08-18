import { ChartFrame } from "@/features/analytics/chart-frame";
import type { SimulationTimelinePoint } from "@/types/results";

interface ConversationVolumeProps {
  timeline: SimulationTimelinePoint[];
}

const WIDTH = 360;
const HEIGHT = 200;
const PAD_X = 28;
const PAD_Y = 28;

export function ConversationVolume({ timeline }: ConversationVolumeProps) {
  const rounds = timeline.filter((point) => point.round > 0);
  const maxValue = Math.max(1, ...rounds.map((point) => point.conversation_count));
  const peak = rounds.reduce(
    (best, point) => (point.conversation_count > best.conversation_count ? point : best),
    rounds[0] ?? timeline[0],
  );
  const plotWidth = WIDTH - PAD_X * 2;
  const barGap = 4;
  const barWidth = Math.max(3, plotWidth / Math.max(1, rounds.length) - barGap);

  return (
    <ChartFrame
      number="04"
      title="Conversation volume"
      description="Scheduled pair conversations completed in each round."
      footer={<span className="chartFootnote mono">Peak: round {peak?.round ?? 0} · {(peak?.conversation_count ?? 0).toLocaleString()} conversations</span>}
    >
      <svg className="analyticsSvg" viewBox={`0 0 ${WIDTH} ${HEIGHT}`} role="img" aria-label="Conversation count by simulation round">
        <line x1={PAD_X} x2={WIDTH - PAD_X} y1={HEIGHT - PAD_Y} y2={HEIGHT - PAD_Y} className="chartAxis" />
        {rounds.map((point, index) => {
          const available = HEIGHT - PAD_Y * 2;
          const barHeight = (point.conversation_count / maxValue) * available;
          const x = PAD_X + index * (barWidth + barGap);
          return (
            <rect
              key={point.round}
              x={x}
              y={HEIGHT - PAD_Y - barHeight}
              width={barWidth}
              height={barHeight}
              rx="2.5"
              className={point.round === peak?.round ? "conversationBar conversationBarPeak" : "conversationBar"}
            >
              <title>{`Round ${point.round}: ${point.conversation_count} conversations`}</title>
            </rect>
          );
        })}
        <text x={PAD_X} y={HEIGHT - 8} className="chartLabel">R1</text>
        <text x={WIDTH - PAD_X} y={HEIGHT - 8} textAnchor="end" className="chartLabel">R{rounds.length}</text>
      </svg>
    </ChartFrame>
  );
}
