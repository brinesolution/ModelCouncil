from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class InfluenceDynamicsConfig:
    version: str = "2j-c-1"
    max_topic_delta: float = 0.20
    saturation_beta: float = 0.95
    base_noise_std: float = 0.012
    noise_floor: float = 0.001
    max_noise_to_signal_ratio: float = 0.35
    weak_tie_exploration_weight: float = 0.45
    disagreement_information_weight: float = 0.08

    def __post_init__(self) -> None:
        if self.max_topic_delta <= 0:
            raise ValueError("max_topic_delta must be positive")
        if self.saturation_beta <= 0:
            raise ValueError("saturation_beta must be positive")
        if self.base_noise_std < 0 or self.noise_floor < 0:
            raise ValueError("noise values cannot be negative")
        if self.max_noise_to_signal_ratio < 0:
            raise ValueError("max_noise_to_signal_ratio cannot be negative")
        if not 0 <= self.weak_tie_exploration_weight <= 1:
            raise ValueError("weak_tie_exploration_weight must be between 0 and 1")
        if self.disagreement_information_weight < 0:
            raise ValueError("disagreement_information_weight cannot be negative")


DEFAULT_INFLUENCE_DYNAMICS = InfluenceDynamicsConfig()
