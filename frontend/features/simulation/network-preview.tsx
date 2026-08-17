import type { SimulationNetworkNode, SimulationRunResponse } from "@/types/results";

interface NetworkPreviewProps {
  network: SimulationRunResponse["network"];
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

export function NetworkPreview({ network }: NetworkPreviewProps) {
  const nodes = network.nodes.slice(0, MAX_NODES);
  const ids = new Set(nodes.map((node) => node.id));
  const points = coordinates(nodes);
  const edges = network.edges.filter((edge) => ids.has(edge.source) && ids.has(edge.target));

  return (
    <section className="resultSection" aria-labelledby="network-title">
      <div className="resultHeader">
        <div>
          <h2 id="network-title">Consumer network preview</h2>
          <p className="muted">A bounded sample of the full KNN graph. Node state reflects final opinion.</p>
        </div>
        <span className="muted">{nodes.length} visible agents</span>
      </div>

      <div className="networkFrame">
        <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} role="img" aria-label="Synthetic consumer social network">
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
                <title>{`Agent ${node.id} · ${node.segment} · opinion ${node.opinion.toFixed(2)}`}</title>
              </circle>
            );
          })}
        </svg>
      </div>
    </section>
  );
}
