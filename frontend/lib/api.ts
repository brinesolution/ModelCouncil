import type {
  FullLiveSimulationRequest,
  FullLiveStartResponse,
  FullLiveStatusResponse,
} from "@/types/full-live";
import type { LlmProviderCatalog } from "@/types/llm-provider";
import type { SimulationRunResponse } from "@/types/results";
import type {
  SimulationPreviewRequest,
  SimulationPreviewResponse,
} from "@/types/simulation";

function normalizeApiBaseUrl(value: string | undefined): string {
  const fallback = "http://127.0.0.1:8000/api/v1";
  const raw = (value ?? fallback).replace(/\/+$/, "");
  return raw.endsWith("/api/v1") ? raw : `${raw}/api/v1`;
}

const API_BASE_URL = normalizeApiBaseUrl(process.env.NEXT_PUBLIC_API_BASE_URL);

async function responseError(response: Response): Promise<Error> {
  const raw = await response.text();
  if (raw) {
    try {
      const payload = JSON.parse(raw) as { detail?: unknown };
      if (typeof payload.detail === "string" && payload.detail.trim()) {
        return new Error(payload.detail);
      }
    } catch {
      // Fall through to the plain response text.
    }
    return new Error(raw);
  }
  return new Error(`API request failed with ${response.status}`);
}

async function postJson<T>(path: string, payload?: unknown): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: payload === undefined ? undefined : JSON.stringify(payload),
  });

  if (!response.ok) {
    throw await responseError(response);
  }
  return (await response.json()) as T;
}

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, { cache: "no-store" });
  if (!response.ok) {
    throw await responseError(response);
  }
  return (await response.json()) as T;
}

export function fetchLlmProviders(): Promise<LlmProviderCatalog> {
  return getJson<LlmProviderCatalog>("/llm/providers");
}

export function previewSimulation(
  payload: SimulationPreviewRequest,
): Promise<SimulationPreviewResponse> {
  return postJson<SimulationPreviewResponse>("/simulations/preview", payload);
}

export function runSimulation(
  payload: SimulationPreviewRequest,
): Promise<SimulationRunResponse> {
  return postJson<SimulationRunResponse>("/simulations/run", payload);
}

export function startFullLiveSimulation(
  payload: FullLiveSimulationRequest,
): Promise<FullLiveStartResponse> {
  return postJson<FullLiveStartResponse>("/simulations/full-live", payload);
}

export function getFullLiveStatus(jobId: string): Promise<FullLiveStatusResponse> {
  return getJson<FullLiveStatusResponse>(`/simulations/full-live/${encodeURIComponent(jobId)}`);
}

export function getFullLiveResult(jobId: string): Promise<SimulationRunResponse> {
  return getJson<SimulationRunResponse>(
    `/simulations/full-live/${encodeURIComponent(jobId)}/result`,
  );
}

export function cancelFullLiveSimulation(jobId: string): Promise<FullLiveStatusResponse> {
  return postJson<FullLiveStatusResponse>(
    `/simulations/full-live/${encodeURIComponent(jobId)}/cancel`,
  );
}
