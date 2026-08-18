from __future__ import annotations

from typing import TYPE_CHECKING

from simulation.config.presets import PopulationPreset, get_population_preset

if TYPE_CHECKING:
    from backend.app.schemas.simulation import SimulationPreviewRequest


MAX_SIMULATION_WORKLOAD = 100_000


def resolve_effective_preset(request: "SimulationPreviewRequest") -> PopulationPreset:
    """Resolve the one numerical preset used by preview, simulation, Full Live, and audit.

    The selected Small/Standard/Large preset remains the template/compatibility label.
    Advanced overrides create a run-local immutable PopulationPreset so lower simulation
    layers never need to know where the values originated.
    """
    base = get_population_preset(request.population_mode.value)
    advanced = request.advanced_config
    if advanced is None:
        return base

    return PopulationPreset(
        name=f"{request.population_mode.value}-advanced",
        population_size=advanced.population_size,
        base_k=advanced.base_k,
        max_conversations_per_round=advanced.max_conversations_per_round,
        initiator_rate=advanced.initiator_rate,
        weak_tie_rate=advanced.weak_tie_rate,
        simulated_minutes_per_round=advanced.simulated_minutes_per_round,
    )


def conversation_upper_bound_for_preset(preset: PopulationPreset, rounds: int) -> int:
    per_round = (preset.population_size * preset.max_conversations_per_round) // 2
    return per_round * rounds


def estimate_conversation_upper_bound(request: "SimulationPreviewRequest") -> int:
    return conversation_upper_bound_for_preset(
        resolve_effective_preset(request),
        request.rounds,
    )
