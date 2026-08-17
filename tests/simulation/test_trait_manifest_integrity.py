import hashlib
import json
from pathlib import Path

from simulation.population.excel_repository import ExcelTraitRepository

TRAIT_ROOT = Path(__file__).resolve().parents[2] / "data" / "traits"
MANIFEST_PATH = TRAIT_ROOT / "catalog.manifest.json"


def _load_manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def test_manifest_references_real_trait_workbooks():
    manifest = _load_manifest()
    declared = {entry["file"] for entry in manifest["workbooks"]}
    actual = {path.name for path in TRAIT_ROOT.glob("*.xlsx")}

    assert declared
    assert actual == declared


def test_trait_workbook_hashes_match_manifest():
    manifest = _load_manifest()

    for entry in manifest["workbooks"]:
        path = TRAIT_ROOT / entry["file"]
        assert path.exists(), f"Missing trait workbook: {entry['file']}"

        payload = path.read_bytes()
        digest = hashlib.sha256(payload).hexdigest()
        assert digest == entry["sha256"], f"Hash mismatch for {entry['file']}"
        assert len(payload) == entry["size_bytes"], f"Size mismatch for {entry['file']}"


def test_real_trait_catalog_loads_required_population_categories():
    catalog = ExcelTraitRepository(TRAIT_ROOT).load_catalog()
    required = {
        "occupations",
        "personality",
        "economic_traits",
        "social_behaviour",
        "technology",
        "consumer_behaviour",
    }

    assert required.issubset(catalog.categories)
    for category in required:
        values = catalog.category(category)
        assert values
        assert abs(sum(value.probability for value in values) - 1.0) < 1e-9
