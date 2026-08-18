"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { LedStatus } from "@/components/industrial/led-status";
import {
  cancelFullLiveSimulation,
  getFullLiveResult,
  getFullLiveStatus,
} from "@/lib/api";
import type { FullLiveStatusResponse } from "@/types/full-live";

const STORAGE_KEY = "modelcouncil:last-simulation";
const POLL_MS = 1500;

function percent(value: number) {
  return `${Math.round(value * 100)}%`;
}

function cost(value: number) {
  return `$${value.toFixed(value < 0.01 ? 6 : 4)}`;
}

function latency(value: number) {
  return value > 0 ? `${Math.round(value)} ms` : "—";
}

function phaseLabel(status: FullLiveStatusResponse["status"] | undefined) {
  switch (status) {
    case "queued": return "Queued";
    case "simulating": return "Deterministic simulation";
    case "rendering": return "Language rendering";
    case "cancelling": return "Stopping new calls";
    case "cancelled": return "Cancelled";
    case "completed": return "Completed";
    case "failed": return "Failed";
    default: return "Connecting";
  }
}

export function FullLiveProgress({ jobId }: { jobId: string }) {
  const router = useRouter();
  const [job, setJob] = useState<FullLiveStatusResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [cancelSubmitting, setCancelSubmitting] = useState(false);

  useEffect(() => {
    let disposed = false;
    let timer: ReturnType<typeof setTimeout> | undefined;

    async function poll() {
      try {
        const next = await getFullLiveStatus(jobId);
        if (disposed) return;
        setJob(next);
        setError(null);

        if (next.status === "completed") {
          const result = await getFullLiveResult(jobId);
          if (disposed) return;
          window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(result));
          router.replace("/simulations/result");
          return;
        }

        if (next.status === "cancelled" || next.status === "failed") {
          return;
        }

        timer = setTimeout(poll, POLL_MS);
      } catch (caught) {
        if (disposed) return;
        setError(
          caught instanceof Error
            ? caught.message
            : "Unable to read the Full Live job. The local backend may have restarted.",
        );
      }
    }

    void poll();
    return () => {
      disposed = true;
      if (timer) clearTimeout(timer);
    };
  }, [jobId, router]);

  async function stopFullLive() {
    const localProvider = job?.llm_provider === "ollama";
    const warning = localProvider
      ? "Stop scheduling additional Full Live local-model calls? In-flight Ollama calls may still finish and continue using local compute."
      : "Stop scheduling additional Full Live cloud-model calls? In-flight calls may still finish and incur usage.";
    if (!window.confirm(warning)) {
      return;
    }
    setCancelSubmitting(true);
    try {
      const updated = await cancelFullLiveSimulation(jobId);
      setJob(updated);
      setError(null);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to cancel the Full Live job.");
    } finally {
      setCancelSubmitting(false);
    }
  }

  const totalLabel = job?.total_conversations === null || job?.total_conversations === undefined
    ? "Pending simulation"
    : job.total_conversations.toLocaleString();
  const active = job && ["queued", "simulating", "rendering", "cancelling"].includes(job.status);
  const localProvider = job?.llm_provider === "ollama";
  const providerLabel = job?.llm_provider === "ollama"
    ? "Ollama Local"
    : job?.llm_provider === "deepseek"
      ? "DeepSeek"
      : "Language provider";
  const ledTone = job?.status === "completed"
    ? "green"
    : job?.status === "failed" || job?.status === "cancelled"
      ? "amber"
      : "red";

  return (
    <main className="page fullLiveProgressPage">
      <div className="fullLiveProgressTopbar">
        <Link href="/simulate" className="textLink">← Simulation console</Link>
        <span className="techLabel">Job {jobId.slice(0, 12)}</span>
      </div>

      <section className="fullLiveProgressConsole">
        <div className="fullLiveProgressHeader">
          <div>
            <span className="techLabel">{localProvider ? "Uncapped local dialogue render" : "Uncapped external dialogue render"}</span>
            <h1>Full Live</h1>
            <p>
              Numerical state is simulated first. Every scheduled conversation is then attempted through the selected language model with bounded concurrency and no hidden total-call cap.
            </p>
          </div>
          <LedStatus label={phaseLabel(job?.status)} tone={ledTone} />
        </div>

        {error ? (
          <div className="fullLiveTerminalMessage fullLiveTerminalError" role="alert">
            <strong>Job connection error</strong>
            <p>{error}</p>
            <p>The current Full Live job store is in-memory. Restarting FastAPI removes its job records.</p>
            <Link href="/simulate" className="button secondary">Return to simulation</Link>
          </div>
        ) : null}

        {job ? (
          <>
            <div className="fullLiveRunMeta">
              <div><span>Product</span><strong>{job.product_name}</strong></div>
              <div><span>Population</span><strong>{job.population_mode}</strong></div>
              <div><span>Rounds</span><strong>{job.rounds}</strong></div>
              <div><span>Seed</span><strong>{job.seed}</strong></div>
              <div><span>Pre-run upper bound</span><strong>{job.estimated_upper_bound_conversations.toLocaleString()}</strong></div>
              <div><span>Exact conversations</span><strong>{totalLabel}</strong></div>
              <div><span>Language source</span><strong>{providerLabel}</strong></div>
              <div><span>Selected model</span><strong>{job.llm_model}</strong></div>
            </div>

            <div className="fullLiveProgressWell" aria-label="Full Live progress">
              <div className="fullLiveProgressReadout">
                <span>{phaseLabel(job.status)}</span>
                <strong>{percent(job.progress_ratio)}</strong>
              </div>
              <div className="fullLiveProgressTrack">
                <i style={{ width: `${Math.max(0, Math.min(100, job.progress_ratio * 100))}%` }} />
              </div>
              <div className="fullLiveProgressCounts mono">
                <span>{job.processed_conversations.toLocaleString()} processed</span>
                <span>{job.successful_renders.toLocaleString()} rendered</span>
                <span>{job.fallback_count.toLocaleString()} fallback</span>
              </div>
            </div>

            <div className="fullLiveTelemetryGrid">
              <div><span>Cache hit ratio</span><strong>{localProvider ? "N/A" : percent(job.cache_hit_ratio)}</strong></div>
              <div><span>Input tokens</span><strong>{job.prompt_tokens.toLocaleString()}</strong></div>
              <div><span>Cache hit tokens</span><strong>{localProvider ? "N/A" : job.prompt_cache_hit_tokens.toLocaleString()}</strong></div>
              <div><span>Output tokens</span><strong>{job.completion_tokens.toLocaleString()}</strong></div>
              <div><span>Total tokens</span><strong>{job.total_tokens.toLocaleString()}</strong></div>
              <div><span>Average latency</span><strong>{latency(job.average_latency_ms)}</strong></div>
              <div><span>Maximum latency</span><strong>{latency(job.max_latency_ms)}</strong></div>
              <div><span>{localProvider ? "Billing" : "Estimated spend"}</span><strong className="fullLiveCost">{localProvider ? "Local compute / no configured API billing" : cost(job.estimated_cost_usd)}</strong></div>
              <div><span>Provider response model</span><strong>{job.provider_model ?? job.llm_model}</strong></div>
            </div>

            {job.status === "cancelled" ? (
              <div className="fullLiveTerminalMessage">
                <strong>Full Live stopped.</strong>
                <p>Usage already incurred is shown above. No completed Results dashboard is created for a cancelled render job.</p>
                <Link href="/simulate" className="button secondary">Configure another run</Link>
              </div>
            ) : null}

            {job.status === "failed" ? (
              <div className="fullLiveTerminalMessage fullLiveTerminalError" role="alert">
                <strong>Full Live job failed.</strong>
                <p>{job.error_message ?? "The backend could not complete this job."}</p>
                <Link href="/simulate" className="button secondary">Return to simulation</Link>
              </div>
            ) : null}

            {active && job.status !== "cancelling" ? (
              <div className="fullLiveStopRow">
                <p>{localProvider ? "Stopping is best-effort. Already in-flight local requests may finish and continue using machine resources." : "Stopping is best-effort. Already in-flight cloud requests may finish and remain billable."}</p>
                <button className="button secondary fullLiveStopButton" type="button" disabled={cancelSubmitting} onClick={stopFullLive}>
                  {cancelSubmitting ? "Stopping…" : "Stop Full Live"}
                </button>
              </div>
            ) : null}
          </>
        ) : (
          <div className="fullLiveProgressWell">
            <div className="fullLiveProgressReadout"><span>Connecting to local job manager</span><strong>—</strong></div>
          </div>
        )}

        <p className="fullLivePersistenceNote mono">
          LOCAL JOB STORAGE · FASTAPI RESTART CLEARS RUNNING AND COMPLETED FULL LIVE JOBS
        </p>
      </section>
    </main>
  );
}
