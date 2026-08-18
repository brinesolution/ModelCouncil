from pathlib import Path

import pytest

from simulation.audit.logger import MemoryRunAuditLogger, NullRunAuditLogger
from simulation.population.excel_repository import ExcelTraitRepository
from simulation.population.generator import generate_population


TRAIT_ROOT = Path("data/traits")


def test_excel_repository_emits_catalog_and_workbook_provenance():
    audit = MemoryRunAuditLogger(run_id="catalog")
    repository = ExcelTraitRepository(TRAIT_ROOT)

    catalog = repository.load_catalog(audit=audit)

    workbook_events = [event for event in audit.events if event["event"] == "traits.workbook"]
    assert workbook_events
    assert len(workbook_events) == len(list(TRAIT_ROOT.glob("*.xlsx")))
    for event in workbook_events:
        payload = event["payload"]
        assert payload["filename"].endswith(".xlsx")
        assert payload["category"] in catalog.categories
        assert payload["schema_version"]
        assert payload["file_size_bytes"] > 0
        assert len(payload["sha256"]) == 64
        assert payload["active_row_count"] > 0
    catalog_events = [event for event in audit.events if event["event"] == "traits.catalog_loaded"]
    assert len(catalog_events) == 1
    assert catalog_events[0]["payload"]["category_count"] == len(catalog.categories)


def test_excel_population_records_sampled_source_keys_and_final_agent_without_changing_population():
    repository = ExcelTraitRepository(TRAIT_ROOT)
    catalog = repository.load_catalog()
    audit = MemoryRunAuditLogger(run_id="population")

    with_audit = generate_population(8, seed=321, traits=repository, audit=audit)
    without_audit = generate_population(8, seed=321, traits=repository, audit=NullRunAuditLogger())

    assert with_audit == without_audit
    generated = [event for event in audit.events if event["event"] == "population.agent_generated"]
    assert len(generated) == 8
    payload = generated[0]["payload"]
    assert payload["source"] == "excel"
    assert set(payload["sampled_sources"]) >= {
        "occupation",
        "personality",
        "economic",
        "social",
        "technology",
        "consumer_behaviour",
    }
    for source in payload["sampled_sources"].values():
        assert source["key"]
        assert source["label"]
        assert 0.0 < source["probability"] <= 1.0
        assert isinstance(source["attributes"], dict)
    trace = payload["correlation_trace"]
    for key in (
        "income",
        "emotionality",
        "logicality",
        "stubbornness",
        "risk_tolerance",
        "sociability",
        "price_sensitivity",
        "technology_adoption",
        "influence_power",
        "brand_loyalty",
    ):
        assert key in trace
        assert "result" in trace[key]
    assert trace["price_sensitivity"]["raw_value"] == pytest.approx(
        trace["price_sensitivity"]["base_price_sensitivity"]
        - trace["price_sensitivity"]["income_adjustment"]
        + trace["price_sensitivity"]["noise"]
    )
    assert trace["logicality"]["center"] == pytest.approx(
        trace["logicality"]["base_logicality_component"]
        + trace["logicality"]["decision_logic_component"]
        + trace["logicality"]["inverse_emotionality_component"]
    )
    assert payload["agent"]["agent_id"] == 0
    assert "traits" in payload["agent"]
    assert "state" in payload["agent"]
    assert 0.0 <= payload["agent"]["income_score"] <= 1.0
    assert catalog.categories


def test_bootstrap_population_provenance_is_observational_only():
    audit = MemoryRunAuditLogger(run_id="bootstrap")

    with_audit = generate_population(6, seed=77, audit=audit)
    without_audit = generate_population(6, seed=77)

    assert with_audit == without_audit
    generated = [event for event in audit.events if event["event"] == "population.agent_generated"]
    assert len(generated) == 6
    assert all(event["payload"]["source"] == "bootstrap" for event in generated)
    assert generated[0]["payload"]["agent"]["agent_id"] == 0
    assert generated[0]["payload"]["generation_inputs"]["occupation"]
