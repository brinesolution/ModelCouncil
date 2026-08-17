"use client";

import Link from "next/link";
import { useMemo, useSyncExternalStore } from "react";

import "../../results.css";
import { NetworkPreview } from "@/features/simulation/network-preview";
import { OpinionTimeline } from "@/features/simulation/opinion-timeline";
import { ResultsSummary } from "@/features/simulation/results-summary";
import type { SimulationRunResponse } from "@/types/results";

const STORAGE_KEY = "modelcouncil:last-simulation";
const noopSubscribe = () => () => undefined;
const getServerSnapshot = () => null;
const getClientSnapshot = () => window.sessionStorage.getItem(STORAGE_KEY);

export default function SimulationResultPage() {
  const rawResult = useSyncExternalStore(
    noopSubscribe,
    getClientSnapshot,
    getServerSnapshot,
  );
  const result = useMemo(() => {
    if (!rawResult) return null;
    try {
      return JSON.parse(rawResult) as SimulationRunResponse;
    } catch {
      return null;
    }
  }, [rawResult]);

  if (!result) {
    return (
      <main className="pageShell">
        <section className="resultSection emptyResult">
          <h1>No simulation result in this tab</h1>
          <p className="muted">Run a product simulation first. Results are kept in this browser tab for the current Phase 1 implementation.</p>
          <Link className="button linkButton" href="/simulate">Create simulation</Link>
        </section>
      </main>
    );
  }

  return (
    <main className="pageShell resultsPage">
      <div className="resultNav">
        <Link href="/simulate" className="textLink">← New simulation</Link>
        <span className="muted">Seed {result.seed} · {result.rounds} rounds · K={result.summary.base_k}</span>
      </div>
      <ResultsSummary result={result} />
      <OpinionTimeline timeline={result.timeline} />
      <NetworkPreview network={result.network} />

      <section className="resultSection" aria-labelledby="conversation-title">
        <div className="resultHeader">
          <div>
            <h2 id="conversation-title">Conversation ledger sample</h2>
            <p className="muted">Phase 1 stores semantic background conversations. Language transcripts are added by the shared LLM layer in the next dialogue phase.</p>
          </div>
        </div>
        <div className="conversationList">
          {result.selected_conversations.length ? result.selected_conversations.map((conversation) => (
            <div className="conversationRow" key={conversation.conversation_id}>
              <span>Round {conversation.round}</span>
              <strong>Agent {conversation.agent_a_id} ↔ Agent {conversation.agent_b_id}</strong>
              <span className="muted">{conversation.topics.join(", ") || "general product discussion"}</span>
            </div>
          )) : <p className="muted">No conversations were scheduled in this run.</p>}
        </div>
      </section>
    </main>
  );
}
