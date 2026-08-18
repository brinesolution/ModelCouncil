from __future__ import annotations

from simulation.population.compatibility import CompatibilityRuleError, parse_compatibility_rule
from simulation.population.trait_repository import TraitCatalog


class TraitCatalogValidationError(ValueError):
    pass


def validate_trait_catalog(catalog: TraitCatalog) -> None:
    if not catalog.categories:
        raise TraitCatalogValidationError("trait catalog is empty")

    for category_key, category in catalog.categories.items():
        if not category.values:
            raise TraitCatalogValidationError(f"category '{category_key}' has no enabled values")

        seen: set[str] = set()
        probability_total = 0.0
        for value in category.values:
            if not value.key:
                raise TraitCatalogValidationError(f"category '{category_key}' contains an empty key")
            if value.key in seen:
                raise TraitCatalogValidationError(
                    f"category '{category_key}' contains duplicate key '{value.key}'"
                )
            seen.add(value.key)

            if not 0.0 <= value.probability <= 1.0:
                raise TraitCatalogValidationError(
                    f"category '{category_key}' value '{value.key}' has invalid probability"
                )
            probability_total += value.probability

            if category_key == "compatibility_rules":
                try:
                    parse_compatibility_rule(value)
                except CompatibilityRuleError as exc:
                    raise TraitCatalogValidationError(str(exc)) from exc

            for attribute_name, attribute_value in value.attributes.items():
                if attribute_name.endswith(("_min", "_max")):
                    continue
                if isinstance(attribute_value, float) and attribute_name not in {
                    "magnitude",
                }:
                    if not -1.0 <= attribute_value <= 1.0:
                        raise TraitCatalogValidationError(
                            f"category '{category_key}' value '{value.key}' attribute "
                            f"'{attribute_name}' is outside expected normalized range"
                        )

        if abs(probability_total - 1.0) > 1e-8:
            raise TraitCatalogValidationError(
                f"category '{category_key}' probabilities sum to {probability_total:.6f}, expected 1.0"
            )
