"use client";

import { useState } from "react";

import { LedStatus } from "@/components/industrial/led-status";
import { PanelDetails } from "@/components/industrial/panel-details";
import { NetworkPreview } from "@/features/simulation/network-preview";
import type { SimulationRunResponse } from "@/types/results";

interface SimulationReplayProps {
  network: SimulationRunResponse["network"];
  replay: SimulationRunResponse["replay"];
}

export function SimulationReplay({ network, replay }: SimulationReplayProps) {
  const [checkpointIndex, setCheckpointIndex] = useState(() =>
    Math.max(0, replay.length - 1),
  );

  if (!replay.length) {
    return (
      <section className="resultSection replaySection">
        <PanelDetails />
        <NetworkPreview network={network} />
      </section>
    );
  }

  const safeIndex = Math.min(checkpointIndex, replay.length - 1);
  const checkpoint = replay[safeIndex];

  return (
    <section className="resultSection replaySection" aria-labelledby="replay-title">
      <PanelDetails />
      <div className="replayControls">
        <div>
          <span className="techLabel">Society replay / temporal state</span>
          <h2 id="replay-title">Round {checkpoint.round}</h2>
          <p>
            {checkpoint.simulated_minutes} simulated minutes · {checkpoint.active_conversations.length} sampled active conversations
          </p>
        </div>
        <div className="replayStatusBlock">
          <LedStatus
            label={checkpoint.active_conversations.length ? "Conversations active" : "Quiet frame"}
            tone={checkpoint.active_conversations.length ? "red" : "green"}
            compact
          />
          <span className="mono">FRAME {String(safeIndex).padStart(2, "0")}/{String(replay.length - 1).padStart(2, "0")}</span>
        </div>
        <div className="replayRangeWrap">
          <label htmlFor="round-replay">Replay round</label>
          <input
            id="round-replay"
            className="replaySlider"
            type="range"
            min={0}
            max={replay.length - 1}
            step={1}
            value={safeIndex}
            onChange={(event) => setCheckpointIndex(Number(event.target.value))}
          />
          <div className="replayScale" aria-hidden="true">
            <span>R{replay[0].round}</span>
            <span>R{replay[replay.length - 1].round}</span>
          </div>
        </div>
      </div>

      <NetworkPreview
        network={network}
        nodeStates={checkpoint.nodes}
        activeConversations={checkpoint.active_conversations}
        round={checkpoint.round}
      />
    </section>
  );
}
