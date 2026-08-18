from pathlib import Path

import pytest

from simulation.audit.logger import MemoryRunAuditLogger
from simulation.domain.agent import AgentState, AgentTraits, ConsumerAgent
from simulation.domain.consumer_context import ConsumerContext, EconomicContext, SocialContext, TechnologyContext
from simulation.population.compatibility import (
    CompatibilityRuleError,
    apply_compatibility_rules,
    parse_compatibility_rule,
)
from simulation.population.excel_repository import ExcelTraitRepository
from simulation.population.generator import generate_population
from simulation.population.trait_repository import TraitValue


TRAIT_ROOT = Path("data/traits")


def _agent() -> ConsumerAgent:
    return ConsumerAgent(
        agent_id=1,
        age=22,
        occupation="Student",
        income_score=0.80,
        traits=AgentTraits(
            sociability=0.85,
            price_sensitivity=0.70,
            technology_adoption=0.90,
            emotionality=0.5,
            logicality=0.6,
            stubbornness=0.75,
            influence_power=0.40,
            product_need=0.5,
            risk_tolerance=0.4,
            brand_loyalty=0.4,
        ),
        state=AgentState(confidence=0.40),
        context=ConsumerContext(
            economic=EconomicContext(discount_sensitivity=0.50),
            social=SocialContext(peer_influence=0.85, social_susceptibility=0.40),
            technology=TechnologyContext(ai_familiarity=0.30, ai_trust=0.60, privacy_concern=0.80),
        ),
    )


def _rule(key: str, condition: str, target: str, effect: str, magnitude: float) -> TraitValue:
    return TraitValue(
        key=key,
        label=key,
        probability=1.0,
        attributes={
            "condition": condition,
            "target": target,
            "effect": effect,
            "magnitude": magnitude,
        },
    )


def test_parse_compatibility_rule_supports_catalog_grammar():
    rule = parse_compatibility_rule(
        _rule("income", "income_score>0.70", "price_sensitivity", "shift", -0.12)
    )

    assert rule.condition_field == "income_score"
    assert rule.operator == ">"
    assert rule.condition_value == pytest.approx(0.70)
    assert rule.target == "price_sensitivity"
    assert rule.effect == "shift"
    assert rule.magnitude == pytest.approx(-0.12)


def test_rules_apply_cap_floor_and_shift_to_active_agent_fields():
    agent = _agent()
    rules = tuple(
        parse_compatibility_rule(value)
        for value in (
            _rule("student_cap", "occupation=student", "income_score", "cap_max", 0.55),
            _rule("tech_floor", "technology_adoption>0.80", "ai_familiarity", "floor_min", 0.55),
            _rule("low_trust", "privacy_concern>0.75", "ai_trust", "shift", -0.16),
            _rule("discount", "income_score<0.90", "discount_sensitivity", "shift", 0.12),
            _rule("peer", "peer_influence>0.75", "social_susceptibility", "floor_min", 0.65),
        )
    )

    applied = apply_compatibility_rules(
        agent,
        rules,
        condition_values={"occupation": "student"},
    )

    assert agent.income_score == pytest.approx(0.55)
    assert agent.context.technology.ai_familiarity == pytest.approx(0.55)
    assert agent.context.technology.ai_trust == pytest.approx(0.44)
    assert agent.context.economic.discount_sensitivity == pytest.approx(0.62)
    assert agent.context.social.social_susceptibility == pytest.approx(0.65)
    assert {item.rule_key for item in applied} == {"student_cap", "tech_floor", "low_trust", "discount", "peer"}


def test_real_excel_population_applies_and_audits_compatibility_rules():
    repository = ExcelTraitRepository(TRAIT_ROOT)
    audit = MemoryRunAuditLogger(run_id="compatibility")

    agents = generate_population(500, seed=1401, traits=repository, audit=audit)

    student_agents = [agent for agent in agents if agent.context.occupation.key == "student"]
    assert student_agents
    assert all(agent.income_score <= 0.55 for agent in student_agents)

    high_tech_agents = [agent for agent in agents if agent.traits.technology_adoption > 0.80]
    assert high_tech_agents
    assert all(agent.context.technology.ai_familiarity >= 0.55 for agent in high_tech_agents)

    rule_events = [event for event in audit.events if event["event"] == "population.compatibility_rule_applied"]
    assert rule_events
    assert {event["payload"]["rule_key"] for event in rule_events} >= {
        "student_income_cap",
        "tech_ai_adoption",
        "occupation_tech_exposure",
    }


def test_unknown_target_or_effect_is_rejected():
    with pytest.raises(CompatibilityRuleError):
        parse_compatibility_rule(_rule("bad-target", "income_score>0.2", "unknown", "shift", 0.1))

    with pytest.raises(CompatibilityRuleError):
        parse_compatibility_rule(_rule("bad-effect", "income_score>0.2", "price_sensitivity", "multiply", 0.1))
