from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from simulation.population.trait_repository import TraitCatalog, TraitCategory, TraitValue
from simulation.population.validator import validate_trait_catalog

REQUIRED_COLUMNS = {"key", "weight", "enabled"}
RESERVED_COLUMNS = {"key", "label", "weight", "enabled"}


class TraitWorkbookError(ValueError):
    pass


class ExcelTraitRepository:
    def __init__(self, root: Path):
        self.root = Path(root)

    def load_catalog(self, validate: bool = True) -> TraitCatalog:
        if not self.root.exists():
            raise TraitWorkbookError(f"trait directory does not exist: {self.root}")

        categories: dict[str, TraitCategory] = {}
        for workbook_path in sorted(self.root.glob("*.xlsx")):
            category = self._load_workbook(workbook_path)
            categories[category.key] = category

        catalog = TraitCatalog(categories=categories)
        if validate:
            validate_trait_catalog(catalog)
        return catalog

    def _load_workbook(self, path: Path) -> TraitCategory:
        try:
            frame = pd.read_excel(path, sheet_name="Traits")
        except ValueError as exc:
            raise TraitWorkbookError(f"{path.name}: missing required 'Traits' sheet") from exc
        except Exception as exc:
            raise TraitWorkbookError(f"{path.name}: failed to read workbook: {exc}") from exc

        missing = REQUIRED_COLUMNS - set(frame.columns)
        if missing:
            missing_text = ", ".join(sorted(missing))
            raise TraitWorkbookError(f"{path.name}: missing required columns: {missing_text}")

        metadata = self._read_metadata(path)
        category_key = str(metadata.get("category") or path.stem).strip()
        schema_version = str(metadata.get("schema_version") or "1.0").strip()

        enabled = frame["enabled"].map(_coerce_bool)
        weights = pd.to_numeric(frame["weight"], errors="coerce")
        active = frame.loc[enabled & weights.gt(0)].copy()
        if active.empty:
            raise TraitWorkbookError(f"{path.name}: no enabled rows with positive weight")

        active["weight"] = pd.to_numeric(active["weight"], errors="raise")
        total_weight = float(active["weight"].sum())
        values: list[TraitValue] = []

        for _, row in active.iterrows():
            key = str(row["key"]).strip()
            if not key or key.lower() == "nan":
                raise TraitWorkbookError(f"{path.name}: contains an empty key")
            label_raw = row.get("label", key)
            label = key if pd.isna(label_raw) else str(label_raw).strip()
            attributes = {
                str(column): _clean_value(row[column])
                for column in active.columns
                if column not in RESERVED_COLUMNS and not pd.isna(row[column])
            }
            values.append(
                TraitValue(
                    key=key,
                    label=label or key,
                    probability=float(row["weight"]) / total_weight,
                    attributes=attributes,
                )
            )

        return TraitCategory(
            key=category_key,
            values=tuple(values),
            schema_version=schema_version,
        )

    @staticmethod
    def _read_metadata(path: Path) -> dict[str, Any]:
        try:
            frame = pd.read_excel(path, sheet_name="Metadata")
        except ValueError:
            return {}
        if not {"field", "value"}.issubset(frame.columns):
            return {}
        return {
            str(row["field"]).strip(): _clean_value(row["value"])
            for _, row in frame.iterrows()
            if not pd.isna(row["field"])
        }


def _clean_value(value: Any) -> Any:
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        try:
            return value.item()
        except ValueError:
            pass
    return value


def _coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and not pd.isna(value):
        return bool(value)
    return str(value).strip().lower() in {"true", "1", "yes", "y", "enabled"}
