import { ChartFrame } from "@/features/analytics/chart-frame";
import type { TopicPressurePoint } from "@/types/results";

interface TopicPressureProps {
  points: TopicPressurePoint[];
}

function signedValues(point: TopicPressurePoint) {
  const support = point.normalized_support ?? point.normalized_score;
  const criticism = point.normalized_criticism ?? 0;
  const net = point.net_score ?? point.raw_score;
  return { support, criticism, net };
}

export function TopicPressure({ points }: TopicPressureProps) {
  const ranked = [...points].sort((a, b) => b.normalized_score - a.normalized_score);
  const strongest = ranked[0];

  return (
    <ChartFrame
      number="05"
      title="Topic support vs criticism"
      description="Signed semantic conversation pressure; synthetic and not causal market importance."
      footer={(
        <span className="chartFootnote mono">
          Highest activity: {strongest?.topic ?? "none"} · left criticism / right support
        </span>
      )}
    >
      <div
        className="topicPressureList topicPressureSignedList"
        role="img"
        aria-label="Topic criticism on the left and support on the right"
      >
        {ranked.map((point) => {
          const { support, criticism, net } = signedValues(point);
          return (
            <div className="topicPressureRow topicPressureSignedRow" key={point.topic}>
              <span className="topicPressureLabel">{point.topic}</span>
              <div className="topicPressureSignedTrack">
                <span className="topicPressureZero" aria-hidden="true" />
                <span
                  className="topicPressureCriticism"
                  style={{ width: `${Math.max(0, Math.min(1, criticism)) * 50}%` }}
                />
                <span
                  className="topicPressureSupport"
                  style={{ width: `${Math.max(0, Math.min(1, support)) * 50}%` }}
                />
              </div>
              <strong className={net < 0 ? "topicNetNegative" : "topicNetPositive"}>
                {net > 0 ? "+" : ""}{net.toFixed(2)}
              </strong>
            </div>
          );
        })}
      </div>
    </ChartFrame>
  );
}
