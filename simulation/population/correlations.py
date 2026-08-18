from __future__ import annotations

import numpy as np


def clip01(value: float) -> float:
    return float(np.clip(value, 0.0, 1.0))


def jitter_normalized(
    rng: np.random.Generator,
    center: float,
    sigma: float = 0.08,
    *,
    trace: dict[str, float] | None = None,
) -> float:
    sampled = float(rng.normal(center, sigma))
    result = clip01(sampled)
    if trace is not None:
        trace.update(
            {
                "center": float(center),
                "sigma": float(sigma),
                "noise": sampled - float(center),
                "raw_value": sampled,
                "result": result,
            }
        )
    return result


def correlated_price_sensitivity(
    rng: np.random.Generator,
    base_price_sensitivity: float,
    income_score: float,
    *,
    trace: dict[str, float] | None = None,
) -> float:
    """Apply a modest income relationship without erasing the sampled economic profile."""
    income_adjustment = (income_score - 0.5) * 0.22
    noise = float(rng.normal(0.0, 0.05))
    raw_value = float(base_price_sensitivity) - income_adjustment + noise
    result = clip01(raw_value)
    if trace is not None:
        trace.update(
            {
                "base_price_sensitivity": float(base_price_sensitivity),
                "income_score": float(income_score),
                "income_adjustment": float(income_adjustment),
                "noise_sigma": 0.05,
                "noise": noise,
                "raw_value": raw_value,
                "result": result,
            }
        )
    return result


def correlated_influence_power(
    rng: np.random.Generator,
    sociability: float,
    base_persuasion: float,
    *,
    decision_social_weight: float = 0.5,
    message_accuracy: float = 0.8,
    trace: dict[str, float] | None = None,
) -> float:
    center = (
        0.08
        + 0.20 * sociability
        + 0.28 * base_persuasion
        + 0.22 * decision_social_weight
        + 0.12 * message_accuracy
    )
    jitter_trace: dict[str, float] = {}
    result = jitter_normalized(rng, center, sigma=0.10, trace=jitter_trace)
    if trace is not None:
        trace.update(
            {
                "base_component": 0.08,
                "sociability": float(sociability),
                "sociability_component": 0.20 * float(sociability),
                "base_persuasion": float(base_persuasion),
                "persuasion_component": 0.28 * float(base_persuasion),
                "decision_social_weight": float(decision_social_weight),
                "decision_social_component": 0.22 * float(decision_social_weight),
                "message_accuracy": float(message_accuracy),
                "message_accuracy_component": 0.12 * float(message_accuracy),
                **jitter_trace,
                "result": result,
            }
        )
    return result


def correlated_logicality(
    rng: np.random.Generator,
    base_logicality: float,
    emotionality: float,
    *,
    decision_logic_weight: float = 0.5,
    trace: dict[str, float] | None = None,
) -> float:
    center = (
        0.45 * base_logicality
        + 0.40 * decision_logic_weight
        + 0.15 * (1.0 - emotionality)
    )
    jitter_trace: dict[str, float] = {}
    result = jitter_normalized(rng, center, sigma=0.10, trace=jitter_trace)
    if trace is not None:
        trace.update(
            {
                "base_logicality": float(base_logicality),
                "base_logicality_component": 0.45 * float(base_logicality),
                "decision_logic_weight": float(decision_logic_weight),
                "decision_logic_component": 0.40 * float(decision_logic_weight),
                "emotionality": float(emotionality),
                "inverse_emotionality_component": 0.15 * (1.0 - float(emotionality)),
                **jitter_trace,
                "result": result,
            }
        )
    return result


def correlated_risk_tolerance(
    rng: np.random.Generator,
    base_risk_tolerance: float,
    *,
    decision_speed: float = 0.5,
    fear_sensitivity: float = 0.5,
    trace: dict[str, float] | None = None,
) -> float:
    center = (
        0.55 * base_risk_tolerance
        + 0.25 * decision_speed
        + 0.20 * (1.0 - fear_sensitivity)
    )
    jitter_trace: dict[str, float] = {}
    result = jitter_normalized(rng, center, sigma=0.10, trace=jitter_trace)
    if trace is not None:
        trace.update(
            {
                "base_risk_tolerance": float(base_risk_tolerance),
                "base_risk_component": 0.55 * float(base_risk_tolerance),
                "decision_speed": float(decision_speed),
                "decision_speed_component": 0.25 * float(decision_speed),
                "fear_sensitivity": float(fear_sensitivity),
                "inverse_fear_component": 0.20 * (1.0 - float(fear_sensitivity)),
                **jitter_trace,
                "result": result,
            }
        )
    return result


def sample_income(
    rng: np.random.Generator,
    minimum: float,
    maximum: float,
    occupation_key: str,
    *,
    trace: dict[str, float | str | bool] | None = None,
) -> float:
    low = clip01(min(minimum, maximum))
    high = clip01(max(minimum, maximum))
    sampled = float(rng.uniform(low, high))
    student_cap_applied = occupation_key == "student" and sampled > 0.55
    capped = min(sampled, 0.55) if occupation_key == "student" else sampled
    result = clip01(capped)
    if trace is not None:
        trace.update(
            {
                "minimum_input": float(minimum),
                "maximum_input": float(maximum),
                "low": low,
                "high": high,
                "occupation_key": occupation_key,
                "uniform_sample": sampled,
                "student_cap": 0.55 if occupation_key == "student" else 1.0,
                "student_cap_applied": student_cap_applied,
                "raw_value": capped,
                "result": result,
            }
        )
    return result
