from __future__ import annotations

from collections import Counter
from pathlib import Path

from simulation.audit.logger import MemoryRunAuditLogger
from simulation.population.excel_repository import ExcelTraitRepository
from simulation.population.generator import generate_population
from simulation.population.social_memberships import assign_social_memberships


TRAIT_ROOT = Path("data/traits")


def _membership_signature(agents):
    return [
        (
            agent.context.memberships.region_id,
            agent.context.memberships.city_id,
            agent.context.memberships.city_tier,
            agent.context.memberships.locality_id,
            agent.context.memberships.household_id,
            agent.context.memberships.workplace_id,
            agent.context.memberships.education_id,
            agent.context.memberships.online_interest_ids,
        )
        for agent in agents
    ]


def test_population_has_persistent_social_membership_context() -> None:
    agents = generate_population(40, seed=901)

    for agent in agents:
        memberships = agent.context.memberships
        assert memberships.region_id != "unspecified"
        assert memberships.city_id != "unspecified"
        assert memberships.city_tier in {1, 2, 3}
        assert memberships.locality_id != "unspecified"
        assert isinstance(memberships.online_interest_ids, tuple)
        assert memberships.online_interest_ids


def test_membership_assignment_is_same_seed_deterministic() -> None:
    first = generate_population(120, seed=902)
    second = generate_population(120, seed=902)

    assert _membership_signature(first) == _membership_signature(second)


def test_excel_population_forms_all_supported_membership_types() -> None:
    agents = generate_population(
        800,
        seed=903,
        traits=ExcelTraitRepository(TRAIT_ROOT),
    )

    households = Counter(
        agent.context.memberships.household_id
        for agent in agents
        if agent.context.memberships.household_id
    )
    workplaces = Counter(
        agent.context.memberships.workplace_id
        for agent in agents
        if agent.context.memberships.workplace_id
    )
    education = Counter(
        agent.context.memberships.education_id
        for agent in agents
        if agent.context.memberships.education_id
    )
    online = Counter(
        group
        for agent in agents
        for group in agent.context.memberships.online_interest_ids
    )

    assert any(size >= 2 for size in households.values())
    assert max(households.values()) <= 6
    assert any(size >= 3 for size in workplaces.values())
    assert education
    assert any(size >= 5 for size in online.values())
    assert len({agent.context.memberships.locality_id for agent in agents}) >= 4


def test_membership_assignment_does_not_mutate_traits_or_product_state() -> None:
    agents = generate_population(120, seed=904)
    before = [
        (
            agent.traits.as_dict(),
            agent.income_score,
            agent.state.overall_opinion,
            agent.state.purchase_intent,
            agent.state.product_salience,
        )
        for agent in agents
    ]

    assign_social_memberships(agents, seed=1904)

    after = [
        (
            agent.traits.as_dict(),
            agent.income_score,
            agent.state.overall_opinion,
            agent.state.purchase_intent,
            agent.state.product_salience,
        )
        for agent in agents
    ]
    assert after == before


def test_membership_assignment_is_audited() -> None:
    audit = MemoryRunAuditLogger(run_id="membership-v3")
    agents = generate_population(80, seed=905, audit=audit)

    summary = [
        event
        for event in audit.events
        if event["event"] == "population.social_memberships_assigned"
    ]
    per_agent = [
        event
        for event in audit.events
        if event["event"] == "population.agent_social_memberships"
    ]

    assert len(summary) == 1
    assert summary[0]["payload"]["population_size"] == len(agents)
    assert summary[0]["payload"]["household_group_count"] > 0
    assert len(per_agent) == len(agents)
