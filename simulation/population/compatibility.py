from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Literal

from simulation.domain.agent import ConsumerAgent, clamp01
from simulation.population.trait_repository import TraitValue


Effect = Literal["cap_max", "floor_min", "shift"]


class CompatibilityRuleError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class CompatibilityRule:
    key: str
    condition_field: str
    operator: str
    condition_value: str | float
    target: str
    effect: Effect
    magnitude: float
    reason: str = ""


@dataclass(frozen=True, slots=True)
class AppliedRule:
    rule_key: str
    target: str
    before: float
    effect: str
    magnitude: float
    after: float


_SUPPORTED_CONDITIONS = {
    "occupation",
    "income_score",
    "stubbornness",
    "technology_adoption",
    "privacy_concern",
    "sociability",
    "tech_exposure",
    "research_tendency",
    "peer_influence",
}
_SUPPORTED_TARGETS = {
    "income_score",
    "price_sensitivity",
    "social_susceptibility",
    "ai_familiarity",
    "ai_trust",
    "influence_power",
    "technology_adoption",
    "confidence",
    "discount_sensitivity",
}
_SUPPORTED_EFFECTS = {"cap_max", "floor_min", "shift"}
_CONDITION_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)(=|>|<)(.+)$")


def parse_compatibility_rule(value: TraitValue) -> CompatibilityRule:
    condition_text = str(value.attributes.get("condition", "")).strip()
    match = _CONDITION_RE.fullmatch(condition_text)
    if match is None:
        raise CompatibilityRuleError(
            f"Compatibility rule {value.key!r} has unsupported condition {condition_text!r}."
        )
    condition_field, operator, raw_condition_value = match.groups()
    if condition_field not in _SUPPORTED_CONDITIONS:
        raise CompatibilityRuleError(
            f"Compatibility rule {value.key!r} uses unsupported condition field {condition_field!r}."
        )

    target = str(value.attributes.get("target", "")).strip()
    if target not in _SUPPORTED_TARGETS:
        raise CompatibilityRuleError(
            f"Compatibility rule {value.key!r} uses unsupported target {target!r}."
        )
    effect = str(value.attributes.get("effect", "")).strip()
    if effect not in _SUPPORTED_EFFECTS:
        raise CompatibilityRuleError(
            f"Compatibility rule {value.key!r} uses unsupported effect {effect!r}."
        )
    try:
        magnitude = float(value.attributes.get("magnitude", 0.0))
    except (TypeError, ValueError) as exc:
        raise CompatibilityRuleError(
            f"Compatibility rule {value.key!r} has a non-numeric magnitude."
        ) from exc

    condition_value: str | float
    try:
        condition_value = float(raw_condition_value)
    except ValueError:
        condition_value = raw_condition_value.strip().lower()

    return CompatibilityRule(
        key=value.key,
        condition_field=condition_field,
        operator=operator,
        condition_value=condition_value,
        target=target,
        effect=effect,  # type: ignore[arg-type]
        magnitude=magnitude,
        reason=str(value.attributes.get("reason", "") or ""),
    )


def apply_compatibility_rules(
    agent: ConsumerAgent,
    rules: tuple[CompatibilityRule, ...],
    *,
    condition_values: dict[str, str | float] | None = None,
) -> list[AppliedRule]:
    extras = condition_values or {}
    applied: list[AppliedRule] = []
    for rule in rules:
        current_condition = _condition_value(agent, rule.condition_field, extras)
        if not _condition_matches(current_condition, rule.operator, rule.condition_value):
            continue

        before = _target_value(agent, rule.target)
        if rule.effect == "cap_max":
            after = min(before, rule.magnitude)
        elif rule.effect == "floor_min":
            after = max(before, rule.magnitude)
        else:
            after = before + rule.magnitude
        after = clamp01(after)
        _set_target_value(agent, rule.target, after)
        applied.append(
            AppliedRule(
                rule_key=rule.key,
                target=rule.target,
                before=before,
                effect=rule.effect,
                magnitude=rule.magnitude,
                after=after,
            )
        )
    return applied


def _condition_matches(current: str | float, operator: str, expected: str | float) -> bool:
    if operator == "=":
        if isinstance(expected, str):
            return str(current).strip().lower() == expected
        return float(current) == expected
    if isinstance(expected, str):
        raise CompatibilityRuleError("Ordering comparisons require numeric condition values.")
    try:
        current_number = float(current)
    except (TypeError, ValueError) as exc:
        raise CompatibilityRuleError("Ordering comparison received a non-numeric field.") from exc
    if operator == ">":
        return current_number > expected
    if operator == "<":
        return current_number < expected
    raise CompatibilityRuleError(f"Unsupported condition operator {operator!r}.")


def _condition_value(
    agent: ConsumerAgent,
    field: str,
    extras: dict[str, str | float],
) -> str | float:
    if field in extras:
        return extras[field]
    mapping: dict[str, str | float] = {
        "occupation": agent.occupation.lower(),
        "income_score": agent.income_score,
        "stubbornness": agent.traits.stubbornness,
        "technology_adoption": agent.traits.technology_adoption,
        "privacy_concern": agent.context.technology.privacy_concern,
        "sociability": agent.traits.sociability,
        "tech_exposure": agent.context.occupation.tech_exposure,
        "research_tendency": agent.context.behaviour.research_tendency,
        "peer_influence": agent.context.social.peer_influence,
    }
    try:
        return mapping[field]
    except KeyError as exc:
        raise CompatibilityRuleError(f"Unsupported condition field {field!r}.") from exc


def _target_value(agent: ConsumerAgent, target: str) -> float:
    mapping = {
        "income_score": lambda: agent.income_score,
        "price_sensitivity": lambda: agent.traits.price_sensitivity,
        "social_susceptibility": lambda: agent.context.social.social_susceptibility,
        "ai_familiarity": lambda: agent.context.technology.ai_familiarity,
        "ai_trust": lambda: agent.context.technology.ai_trust,
        "influence_power": lambda: agent.traits.influence_power,
        "technology_adoption": lambda: agent.traits.technology_adoption,
        "confidence": lambda: agent.state.confidence,
        "discount_sensitivity": lambda: agent.context.economic.discount_sensitivity,
    }
    try:
        return float(mapping[target]())
    except KeyError as exc:
        raise CompatibilityRuleError(f"Unsupported target {target!r}.") from exc


def _set_target_value(agent: ConsumerAgent, target: str, value: float) -> None:
    if target == "income_score":
        agent.income_score = value
    elif target == "price_sensitivity":
        agent.traits.price_sensitivity = value
    elif target == "social_susceptibility":
        agent.context.social.social_susceptibility = value
    elif target == "ai_familiarity":
        agent.context.technology.ai_familiarity = value
    elif target == "ai_trust":
        agent.context.technology.ai_trust = value
    elif target == "influence_power":
        agent.traits.influence_power = value
    elif target == "technology_adoption":
        agent.traits.technology_adoption = value
    elif target == "confidence":
        agent.state.confidence = value
    elif target == "discount_sensitivity":
        agent.context.economic.discount_sensitivity = value
    else:
        raise CompatibilityRuleError(f"Unsupported target {target!r}.")
