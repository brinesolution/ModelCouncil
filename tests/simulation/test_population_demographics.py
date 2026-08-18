from pathlib import Path

from simulation.audit.logger import MemoryRunAuditLogger
from simulation.population.excel_repository import ExcelTraitRepository
from simulation.population.generator import generate_population


TRAIT_ROOT = Path("data/traits")


def test_excel_population_samples_demographics_and_can_generate_older_consumers():
    repository = ExcelTraitRepository(TRAIT_ROOT)
    audit = MemoryRunAuditLogger(run_id="demographics")

    agents = generate_population(1200, seed=917, traits=repository, audit=audit)

    assert max(agent.age for agent in agents) > 55
    assert max(agent.age for agent in agents) <= 68
    assert any(agent.context.demographic.key != "unspecified" for agent in agents)

    generated = [event for event in audit.events if event["event"] == "population.agent_generated"]
    assert len(generated) == 1200
    assert all("demographic" in event["payload"]["sampled_sources"] for event in generated)


def test_generated_age_respects_sampled_demographic_range_and_occupation_minimum():
    repository = ExcelTraitRepository(TRAIT_ROOT)
    audit = MemoryRunAuditLogger(run_id="demographic-age")

    generate_population(500, seed=918, traits=repository, audit=audit)

    for event in audit.events:
        if event["event"] != "population.agent_generated":
            continue
        payload = event["payload"]
        demographic = payload["sampled_sources"]["demographic"]["attributes"]
        occupation = payload["sampled_sources"]["occupation"]["attributes"]
        age = payload["agent"]["age"]
        expected_min = max(int(demographic["age_min"]), int(occupation["min_age"]))
        expected_max = int(demographic["age_max"])

        assert expected_min <= age <= expected_max
        assert payload["generation_inputs"]["effective_age_min"] == expected_min
        assert payload["generation_inputs"]["effective_age_max"] == expected_max


def test_excel_demographic_generation_is_reproducible():
    repository = ExcelTraitRepository(TRAIT_ROOT)

    first = generate_population(80, seed=919, traits=repository)
    second = generate_population(80, seed=919, traits=repository)

    assert [(agent.age, agent.occupation, agent.context.demographic.key) for agent in first] == [
        (agent.age, agent.occupation, agent.context.demographic.key) for agent in second
    ]
