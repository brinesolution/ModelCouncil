from fastapi import APIRouter

from backend.app.schemas.simulation import (
    SimulationPreviewRequest,
    SimulationPreviewResponse,
    SimulationRunResponse,
)
from backend.app.services.simulation_service import build_simulation_preview, run_simulation

router = APIRouter(prefix="/simulations", tags=["simulations"])


@router.post("/preview", response_model=SimulationPreviewResponse)
def preview_simulation(request: SimulationPreviewRequest) -> SimulationPreviewResponse:
    return build_simulation_preview(request)


@router.post("/run", response_model=SimulationRunResponse)
def execute_simulation(request: SimulationPreviewRequest) -> SimulationRunResponse:
    return run_simulation(request)
