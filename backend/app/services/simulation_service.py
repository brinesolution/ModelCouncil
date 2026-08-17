from backend.app.schemas.simulation import (
    SimulationPreviewRequest,
    SimulationPreviewResponse,
    SimulationPresetView,
)
from simulation.config.presets import get_population_preset


def build_simulation_preview(
    request: SimulationPreviewRequest,
) -> SimulationPreviewResponse:
    preset = get_population_preset(request.population_mode.value)

    return SimulationPreviewResponse(
        status="initialized",
        product_name=request.product.name,
        preset=SimulationPresetView(
            population_size=preset.population_size,
            base_k=preset.base_k,
            max_conversations_per_round=preset.max_conversations_per_round,
            initiator_rate=preset.initiator_rate,
            weak_tie_rate=preset.weak_tie_rate,
            simulated_minutes_per_round=preset.simulated_minutes_per_round,
        ),
        rounds=request.rounds,
        dialogue_mode=request.dialogue_mode,
        seed=request.seed,
        note=(
            "Initialization preview only. Population generation, KNN construction, "
            "dialogue scheduling, and synchronous opinion updates are implemented "
            "as separate simulation modules and will be connected incrementally."
        ),
    )
