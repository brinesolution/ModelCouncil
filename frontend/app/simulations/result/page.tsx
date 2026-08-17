"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import "../../results.css";
import { NetworkPreview } from "@/features/simulation/network-preview";
import { OpinionTimeline } from "@/features/simulation/opinion-timeline";
import { ResultsSummary } from "@/features/simulation/results-summary";
import type { SimulationRunResponse } from "@/types/results";

const STORAGE_KEY = "modelcouncil:last-simulation";

export default function SimulationResultPage() {
  const [result, setResult] = useState<SimulationRunResponse | null>(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    const stored = window.sessionStorage.getItem(STORAGE_KEY);
    if (stored) {
      try {
        setResult(JSON.parse(stored) as SimulationRunResponse);
      } catch {
        window.sessionStorage.removeItem(STORAGE_KEY);
      }
    }
    setLoaded(true);
  }, []);

  if (!loaded) {
    return <main className="pageShell"><p className="muted">Loading simulation result…</p></main>;
  }

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
