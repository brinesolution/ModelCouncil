"use client";

import Link from "next/link";
import { useMemo, useSyncExternalStore } from "react";

import "../../results.css";
import { AnalyticsGrid } from "@/features/analytics/analytics-grid";
import { ConversationLedger } from "@/features/simulation/conversation-ledger";
import { ResultsSummary } from "@/features/simulation/results-summary";
import { SimulationReplay } from "@/features/simulation/simulation-replay";
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
          <span className="techLabel">No local run detected</span>
          <h1>No simulation result in this tab</h1>
          <p>
            Run a product simulation first. Results are stored in this browser tab for the current local implementation.
          </p>
          <Link className="button linkButton" href="/simulate">Create simulation</Link>
        </section>
      </main>
    );
  }

  if (!result.analytics) {
    return (
      <main className="pageShell">
        <section className="resultSection emptyResult">
          <span className="techLabel">Stored result schema outdated</span>
          <h1>Run the simulation again for the new analytics dashboard</h1>
          <p>
            This browser tab contains a result created before the six-chart analytics payload was added. Re-running the same seeded configuration will generate the new response shape.
          </p>
          <Link className="button linkButton" href="/simulate">Run updated simulation</Link>
        </section>
      </main>
    );
  }

  return (
    <main className="pageShell resultsPage">
      <div className="resultNav">
        <Link href="/simulate" className="consoleBackLink">← New simulation</Link>
        <div className="resultRunMeta">
          <span className="runMetaLight" aria-hidden="true" />
          <span>SEED {result.seed}</span>
          <span>R{result.rounds}</span>
          <span>K{result.summary.base_k}</span>
          <span>{result.population_mode.toUpperCase()}</span>
        </div>
      </div>

      <ResultsSummary result={result} />
      <AnalyticsGrid result={result} />
      <SimulationReplay network={result.network} replay={result.replay} />
      <ConversationLedger conversations={result.selected_conversations} />
    </main>
  );
}
