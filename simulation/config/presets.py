from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PopulationPreset:
    name: str
    population_size: int
    base_k: int
    max_conversations_per_round: int
    initiator_rate: float
    weak_tie_rate: float
    simulated_minutes_per_round: int


PRESETS: dict[str, PopulationPreset] = {
    "small": PopulationPreset(
        name="small",
        population_size=250,
        base_k=10,
        max_conversations_per_round=2,
        initiator_rate=0.20,
        weak_tie_rate=0.05,
        simulated_minutes_per_round=5,
    ),
    "standard": PopulationPreset(
        name="standard",
        population_size=1000,
        base_k=14,
        max_conversations_per_round=2,
        initiator_rate=0.20,
        weak_tie_rate=0.05,
        simulated_minutes_per_round=5,
    ),
    "large": PopulationPreset(
        name="large",
        population_size=5000,
        base_k=18,
        max_conversations_per_round=2,
        initiator_rate=0.20,
        weak_tie_rate=0.05,
        simulated_minutes_per_round=5,
    ),
}


def get_population_preset(name: str) -> PopulationPreset:
    try:
        return PRESETS[name]
    except KeyError as exc:
        allowed = ", ".join(sorted(PRESETS))
        raise ValueError(f"Unknown population preset '{name}'. Expected: {allowed}.") from exc
