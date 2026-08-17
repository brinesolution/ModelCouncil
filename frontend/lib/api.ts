import type {
  SimulationPreviewRequest,
  SimulationPreviewResponse,
} from "@/types/simulation";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000/api/v1";

export async function previewSimulation(
  payload: SimulationPreviewRequest,
): Promise<SimulationPreviewResponse> {
  const response = await fetch(`${API_BASE_URL}/simulations/preview`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `API request failed with ${response.status}`);
  }

  return (await response.json()) as SimulationPreviewResponse;
}
