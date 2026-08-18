from pathlib import Path

import pandas as pd
import pytest

from simulation.population.excel_repository import ExcelTraitRepository
from simulation.population.validator import TraitCatalogValidationError, validate_trait_catalog


def create_test_workbook(path: Path, rows: list[dict]) -> None:
    frame = pd.DataFrame(rows)
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        frame.to_excel(writer, sheet_name="Traits", index=False)
        pd.DataFrame(
            [
                {"field": "schema_version", "value": "1.0"},
                {"field": "category", "value": path.stem},
            ]
        ).to_excel(writer, sheet_name="Metadata", index=False)


def test_excel_repository_normalizes_sampling_weights(tmp_path: Path):
    workbook = tmp_path / "personality.xlsx"
    create_test_workbook(
        workbook,
        rows=[
            {"key": "analytical", "label": "Analytical", "weight": 2.0, "enabled": True},
            {"key": "emotional", "label": "Emotional", "weight": 1.0, "enabled": True},
            {"key": "disabled", "label": "Disabled", "weight": 10.0, "enabled": False},
        ],
    )

    catalog = ExcelTraitRepository(tmp_path).load_catalog()
    values = catalog.category("personality")

    assert [item.key for item in values] == ["analytical", "emotional"]
    assert values[0].probability == pytest.approx(2 / 3)
    assert values[1].probability == pytest.approx(1 / 3)


def test_excel_repository_preserves_category_specific_attributes(tmp_path: Path):
    workbook = tmp_path / "personality.xlsx"
    create_test_workbook(
        workbook,
        rows=[
            {
                "key": "analytical",
                "label": "Analytical",
                "weight": 1.0,
                "enabled": True,
                "logicality": 0.9,
                "emotionality": 0.2,
            }
        ],
    )

    item = ExcelTraitRepository(tmp_path).load_catalog().category("personality")[0]

    assert item.attributes["logicality"] == pytest.approx(0.9)
    assert item.attributes["emotionality"] == pytest.approx(0.2)


def test_excel_repository_ignores_microsoft_office_lock_files(tmp_path: Path):
    workbook = tmp_path / "personality.xlsx"
    create_test_workbook(
        workbook,
        rows=[
            {"key": "balanced", "label": "Balanced", "weight": 1.0, "enabled": True},
        ],
    )
    (tmp_path / "~$personality.xlsx").write_text("office lock placeholder", encoding="utf-8")

    catalog = ExcelTraitRepository(tmp_path).load_catalog()

    assert [item.key for item in catalog.category("personality")] == ["balanced"]


def test_validator_rejects_duplicate_keys(tmp_path: Path):
    workbook = tmp_path / "personality.xlsx"
    create_test_workbook(
        workbook,
        rows=[
            {"key": "same", "label": "First", "weight": 1.0, "enabled": True},
            {"key": "same", "label": "Second", "weight": 1.0, "enabled": True},
        ],
    )

    catalog = ExcelTraitRepository(tmp_path).load_catalog(validate=False)

    with pytest.raises(TraitCatalogValidationError, match="duplicate key"):
        validate_trait_catalog(catalog)
