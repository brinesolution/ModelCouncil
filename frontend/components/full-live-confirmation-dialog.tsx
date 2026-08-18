"use client";

import { useEffect, useRef, useState } from "react";

import type { LlmSelection } from "@/types/llm-provider";

interface FullLiveConfirmationDialogProps {
  upperBoundCalls: number;
  selection: LlmSelection;
  onCancel: () => void;
  onConfirm: () => void;
}

const HIGH_COST_THRESHOLD = 5_000;

export function FullLiveConfirmationDialog({
  upperBoundCalls,
  selection,
  onCancel,
  onConfirm,
}: FullLiveConfirmationDialogProps) {
  const highCost = upperBoundCalls > HIGH_COST_THRESHOLD;
  const localProvider = selection.provider.kind === "local";
  const [acknowledgement, setAcknowledgement] = useState("");
  const firstControlRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    firstControlRef.current?.focus();
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") onCancel();
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onCancel]);

  const confirmed = !highCost || acknowledgement === "FULL LIVE";

  return (
    <div className="fullLiveModalBackdrop" role="presentation" onMouseDown={onCancel}>
      <section
        className="fullLiveModal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="full-live-title"
        aria-describedby="full-live-description"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <div className="fullLiveModalHeader">
          <span className="fullLiveWarningLight" aria-hidden="true" />
          <div>
            <span className="techLabel">
              {localProvider ? "Local model execution / uncapped mode" : "External model execution / uncapped mode"}
            </span>
            <h2 id="full-live-title">Confirm Full Live — {selection.provider.label}</h2>
          </div>
        </div>

        <div id="full-live-description" className="fullLiveWarningBody">
          <p>
            Every conversation that ModelCouncil schedules in this run will be rendered by <strong>{selection.model.label}</strong> after the deterministic simulation finishes.
          </p>
          <div className="fullLiveCallReadout">
            <span>Conservative call upper bound</span>
            <strong>{upperBoundCalls.toLocaleString()}</strong>
          </div>

          {localProvider ? (
            <ul>
              <li>This mode has no hidden total model-call cap.</li>
              <li>Local inference can heavily use CPU, GPU, VRAM/RAM, and may take substantially longer.</li>
              <li>ModelCouncil does not apply DeepSeek/cloud API billing to this Ollama Local run.</li>
              <li>Product and synthetic-agent context is sent to the server-configured local Ollama endpoint.</li>
              <li>The model changes wording only; numerical simulation state remains deterministic.</li>
              <li>Closing or cancelling this dialog starts no Full Live model calls.</li>
            </ul>
          ) : (
            <ul>
              <li>This mode has no hidden total external-model call cap.</li>
              <li>API charges can accumulate and the run may take minutes or longer.</li>
              <li>Your product pitch and synthetic-agent dialogue context are sent to {selection.provider.label} for wording.</li>
              <li>The model changes wording only; numerical simulation state remains deterministic.</li>
              <li>Closing or cancelling this dialog starts no Full Live model calls.</li>
            </ul>
          )}
        </div>

        {highCost ? (
          <div className="fullLiveTypedAck">
            <label htmlFor="full-live-ack">
              High-call run: type <strong>FULL LIVE</strong> to acknowledge the risk.
            </label>
            <input
              id="full-live-ack"
              value={acknowledgement}
              onChange={(event) => setAcknowledgement(event.target.value)}
              autoComplete="off"
              spellCheck={false}
              placeholder="FULL LIVE"
            />
          </div>
        ) : null}

        <div className="fullLiveModalActions">
          <button ref={firstControlRef} className="button secondary" type="button" onClick={onCancel}>
            Cancel
          </button>
          <button
            className="button fullLiveDangerButton"
            type="button"
            disabled={!confirmed}
            onClick={onConfirm}
          >
            Start Full Live
          </button>
        </div>
      </section>
    </div>
  );
}
