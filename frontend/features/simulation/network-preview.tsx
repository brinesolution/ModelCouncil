import { LedStatus } from "@/components/industrial/led-status";
import type {
  SimulationNetworkNode,
  SimulationReplayAgentState,
  SimulationReplayConversation,
  SimulationRunResponse,
} from "@/types/results";

interface NetworkPreviewProps {
  network: SimulationRunResponse["network"];
  nodeStates?: SimulationReplayAgentState[];
  activeConversations?: SimulationReplayConversation[];
  round?: number;
}

const WIDTH = 760;
const HEIGHT = 420;
const MAX_NODES = 36;

function coordinates(nodes: SimulationNetworkNode[]) {
  const centerX = WIDTH / 2;
  const centerY = HEIGHT / 2;
  return new Map(
    nodes.map((node, index) => {
      const ring = Math.floor(index / 12);
      const ringIndex = index % 12;
      const ringSize = Math.min(12, nodes.length - ring * 12);
      const angle = (ringIndex / Math.max(1, ringSize)) * Math.PI * 2 + ring * 0.25;
      const radius = 95 + ring * 58;
      return [
        node.id,
        {
          x: centerX + Math.cos(angle) * radius,
          y: centerY + Math.sin(angle) * radius,
        },
      ];
    }),
  );
}

function opinionClass(opinion: number) {
  if (opinion > 0.2) return "networkPositive";
  if (opinion < -0.2) return "networkNegative";
  return "networkNeutral";
}

export function NetworkPreview({
  network,
  nodeStates = [],
  activeConversations = [],
  round,
}: NetworkPreviewProps) {
  const replayById = new Map(nodeStates.map((state) => [state.id, state]));
  const nodes = network.nodes.slice(0, MAX_NODES).map((node) => {
    const state = replayById.get(node.id);
    return state
      ? {
          ...node,
          opinion: state.opinion,
          purchase_intent: state.purchase_intent,
        }
      : node;
  });
  const ids = new Set(nodes.map((node) => node.id));
  const points = coordinates(nodes);
  const edges = network.edges.filter((edge) => ids.has(edge.source) && ids.has(edge.target));
  const activeVisible = activeConversations.filter(
    (conversation) => ids.has(conversation.source) && ids.has(conversation.target),
  );

  return (
    <section className="networkReplayPanel" aria-labelledby="network-title">
      <div className="networkPanelHeader">
        <div>
          <span className="techLabel">Network field / sampled topology</span>
          <h3 id="network-title">Consumer interaction map</h3>
          <p>
            Node size reflects influence. Opinion state changes with the selected replay round; signal-red edges are active conversations.
          </p>
        </div>
        <div className="networkPanelStatus">
          <LedStatus label={activeVisible.length ? "Signal active" : "Monitoring"} tone={activeVisible.length ? "red" : "green"} compact />
          <span className="mono">{round === undefined ? "FINAL" : `R${round}`} / {nodes.length} NODES</span>
        </div>
      </div>

      <div className="networkFrame">
        <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} role="img" aria-label="Synthetic consumer social network replay">
          <defs>
            <radialGradient id="networkGlow" cx="50%" cy="42%" r="70%">
              <stop offset="0%" stopColor="#b92b3c" stopOpacity="0.10" />
              <stop offset="100%" stopColor="#101318" stopOpacity="0" />
            </radialGradient>
          </defs>
          <rect width={WIDTH} height={HEIGHT} fill="url(#networkGlow)" />
          {edges.map((edge) => {
            const source = points.get(edge.source);
            const target = points.get(edge.target);
            if (!source || !target) return null;
            return (
              <line
                key={`${edge.source}-${edge.target}`}
                x1={source.x}
                y1={source.y}
                x2={target.x}
                y2={target.y}
                className={edge.weak_tie ? "networkEdge networkEdgeWeak" : "networkEdge"}
              />
            );
          })}
          {activeVisible.map((conversation) => {
            const source = points.get(conversation.source);
            const target = points.get(conversation.target);
            if (!source || !target) return null;
            return (
              <line
                key={`active-${conversation.conversation_id}`}
                x1={source.x}
                y1={source.y}
                x2={target.x}
                y2={target.y}
                className="networkEdgeActive"
              />
            );
          })}
          {nodes.map((node) => {
            const point = points.get(node.id);
            if (!point) return null;
            const radius = 5 + node.influence * 5;
            return (
              <circle
                key={node.id}
                cx={point.x}
                cy={point.y}
                r={radius}
                className={`networkNode ${opinionClass(node.opinion)}`}
              >
                <title>{`Agent ${node.id} · ${node.segment} · opinion ${node.opinion.toFixed(2)} · purchase ${Math.round(node.purchase_intent * 100)}%`}</title>
              </circle>
            );
          })}
        </svg>
        <div className="networkLegend" aria-label="Network opinion legend">
          <span><i className="legendDot networkPositive" />Positive</span>
          <span><i className="legendDot networkNeutral" />Neutral</span>
          <span><i className="legendDot networkNegative" />Negative</span>
          <span><i className="legendLine activeLegendLine" />Active conversation</span>
        </div>
      </div>
    </section>
  );
}
