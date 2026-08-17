import type { SimulationRunResponse } from "@/types/results";
import type {
  SimulationPreviewRequest,
  SimulationPreviewResponse,
} from "@/types/simulation";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1";

async function postJson<T>(path: string, payload: SimulationPreviewRequest): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `API request failed with ${response.status}`);
  }

  return (await response.json()) as T;
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
