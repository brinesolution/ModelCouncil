from simulation.config.presets import get_population_preset


def test_standard_preset_matches_behavior_specification() -> None:
    preset = get_population_preset("standard")

    assert preset.population_size == 1000
    assert preset.base_k == 14
    assert preset.max_conversations_per_round == 2
    assert preset.initiator_rate == 0.20
    assert preset.weak_tie_rate == 0.05
    assert preset.simulated_minutes_per_round == 5
