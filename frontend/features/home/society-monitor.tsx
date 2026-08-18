import { LedStatus } from "@/components/industrial/led-status";
import { PanelDetails } from "@/components/industrial/panel-details";

const NODES = [
  [72, 92], [132, 54], [198, 98], [252, 54], [318, 92], [116, 158],
  [186, 150], [268, 162], [86, 232], [162, 222], [238, 232], [318, 220],
  [132, 296], [210, 286], [286, 300],
] as const;

const EDGES = [
  [0, 1], [0, 5], [1, 2], [1, 6], [2, 3], [2, 6], [2, 7], [3, 4], [3, 7],
  [5, 6], [5, 8], [5, 9], [6, 7], [6, 9], [6, 10], [7, 10], [7, 11], [8, 9],
  [8, 12], [9, 10], [9, 12], [9, 13], [10, 11], [10, 13], [10, 14], [11, 14],
  [12, 13], [13, 14],
] as const;

export function SocietyMonitor() {
  return (
    <div className="deviceShell" aria-label="Synthetic society monitor illustration">
      <PanelDetails screws vents={false} />
      <div className="deviceTopline">
        <LedStatus label="Society online" tone="red" compact />
        <span className="techLabel">MC-01 / LIVE MODEL</span>
      </div>

      <div className="deviceScreen">
        <svg viewBox="0 0 390 350" role="img" aria-label="Connected synthetic consumer network">
          <defs>
            <radialGradient id="monitorGlow" cx="35%" cy="30%" r="65%">
              <stop offset="0%" stopColor="#b92b3c" stopOpacity="0.24" />
              <stop offset="100%" stopColor="#101318" stopOpacity="0" />
            </radialGradient>
          </defs>
          <rect width="390" height="350" fill="url(#monitorGlow)" />
          {EDGES.map(([sourceIndex, targetIndex], index) => {
            const source = NODES[sourceIndex];
            const target = NODES[targetIndex];
            const active = index === 10 || index === 18;
            return (
              <line
                key={`${sourceIndex}-${targetIndex}`}
                x1={source[0]}
                y1={source[1]}
                x2={target[0]}
                y2={target[1]}
                stroke={active ? "#d33d4f" : "#4a515d"}
                strokeWidth={active ? 2.1 : 1}
                opacity={active ? 0.95 : 0.55}
              />
            );
          })}
          {NODES.map(([x, y], index) => {
            const hot = [1, 6, 10, 13].includes(index);
            return (
              <g key={`${x}-${y}`}>
                {hot ? <circle cx={x} cy={y} r="10" fill="#b92b3c" opacity="0.12" /> : null}
                <circle
                  cx={x}
                  cy={y}
                  r={hot ? 5.3 : 4}
                  fill={hot ? "#ef5b68" : "#c5ccd6"}
                  stroke={hot ? "#ffd9de" : "#727b88"}
                  strokeWidth="1"
                />
              </g>
            );
          })}
          <polyline
            points="26,324 74,318 112,322 152,307 194,311 238,296 276,303 318,286 362,292"
            fill="none"
            stroke="#d33d4f"
            strokeWidth="2.2"
            strokeLinejoin="round"
            strokeLinecap="round"
          />
          <line x1="24" y1="333" x2="366" y2="333" stroke="#39404a" strokeWidth="1" />
          <text x="24" y="25" fill="#8f9aa8" fontSize="10" fontFamily="monospace" letterSpacing="1.4">
            ACTIVE CONVERSATION FIELD
          </text>
        </svg>
      </div>

      <div className="deviceFooter">
        <span className="techLabel">Opinion propagation / replay ready</span>
        <div className="deviceKeys" aria-hidden="true">
          <i /><i /><i /><i />
        </div>
      </div>
    </div>
  );
}
