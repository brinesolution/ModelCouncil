from fastapi import APIRouter

from backend.app.schemas.simulation import (
    SimulationPreviewRequest,
    SimulationPreviewResponse,
)
from backend.app.services.simulation_service import build_simulation_preview

router = APIRouter(prefix="/simulations", tags=["simulations"])


@router.post("/preview", response_model=SimulationPreviewResponse)
def preview_simulation(request: SimulationPreviewRequest) -> SimulationPreviewResponse:
    return build_simulation_preview(request)
