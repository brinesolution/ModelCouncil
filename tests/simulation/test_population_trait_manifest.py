from pathlib import Path

from simulation.population.activation import activation_for, trait_activation_manifest
from simulation.population.excel_repository import ExcelTraitRepository


TRAIT_ROOT = Path("data/traits")


def test_every_loaded_trait_attribute_declares_an_activation_status():
    catalog = ExcelTraitRepository(TRAIT_ROOT).load_catalog()

    missing: list[tuple[str, str]] = []
    for category_key, category in catalog.categories.items():
        for column in sorted({key for value in category.values for key in value.attributes}):
            if activation_for(category_key, column) is None:
                missing.append((category_key, column))

    assert missing == []


def test_manifest_distinguishes_active_derived_and_provenance_only_fields():
    manifest = trait_activation_manifest()
    statuses = {item.status for item in manifest}

    assert statuses == {"active", "derived", "provenance_only"}
    assert activation_for("demographics", "age_max").status == "derived"
    assert activation_for("technology", "ai_trust").consumer_path == "context.technology.ai_trust"
    assert activation_for("consumer_behaviour", "description").status == "provenance_only"
