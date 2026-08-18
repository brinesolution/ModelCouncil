from __future__ import annotations

from dataclasses import dataclass

from simulation.product.taxonomy import ProductTaxonomy


@dataclass(frozen=True, slots=True)
class PriceReference:
    family: str
    form: str
    cadence: str
    reference_price_inr: float
    source: str


_FAMILY_FALLBACKS: dict[str, dict[str, float]] = {
    "software_subscription": {"one_time": 4500.0, "monthly": 600.0, "yearly": 6000.0},
    "consumer_electronics": {"one_time": 12000.0, "monthly": 1200.0, "yearly": 12000.0},
    "smart_home": {"one_time": 6000.0, "monthly": 700.0, "yearly": 7000.0},
    "fitness_wellness": {"one_time": 3500.0, "monthly": 650.0, "yearly": 6000.0},
    "education_productivity": {"one_time": 2500.0, "monthly": 400.0, "yearly": 4000.0},
    "personal_care_luxury": {"one_time": 5000.0, "monthly": 1000.0, "yearly": 10000.0},
    "security_privacy": {"one_time": 2500.0, "monthly": 300.0, "yearly": 3000.0},
    "general": {"one_time": 5000.0, "monthly": 500.0, "yearly": 5000.0},
}

# Simulation calibration anchors, not claims of current market prices.  The
# values deliberately separate product forms that were previously collapsed
# into a single broad-family reference.
_FORM_REFERENCES: dict[str, dict[str, float]] = {
    "fitness_service": {"one_time": 3500.0, "monthly": 650.0, "yearly": 6000.0},
    "indoor_security_camera": {"one_time": 4000.0, "monthly": 450.0, "yearly": 4500.0},
    "finance_software": {"one_time": 3000.0, "monthly": 500.0, "yearly": 5000.0},
    "audio_earbuds": {"one_time": 6000.0, "monthly": 800.0, "yearly": 8000.0},
    "beauty_device": {"one_time": 6500.0, "monthly": 900.0, "yearly": 9000.0},
    "education_software": {"one_time": 3000.0, "monthly": 500.0, "yearly": 5000.0},
    "meal_planning_software": {"one_time": 2500.0, "monthly": 500.0, "yearly": 5000.0},
    "vpn_service": {"one_time": 2200.0, "monthly": 300.0, "yearly": 3000.0},
    "robot_vacuum": {"one_time": 18000.0, "monthly": 1500.0, "yearly": 15000.0},
    "business_saas": {"one_time": 6500.0, "monthly": 900.0, "yearly": 9000.0},
    "portable_power_bank": {"one_time": 3000.0, "monthly": 500.0, "yearly": 5000.0},
    "fragrance": {"one_time": 4500.0, "monthly": 800.0, "yearly": 8000.0},
    "smart_home_device": {"one_time": 6000.0, "monthly": 700.0, "yearly": 7000.0},
    "personal_care": {"one_time": 5000.0, "monthly": 1000.0, "yearly": 10000.0},
}


def resolve_price_reference(taxonomy: ProductTaxonomy, cadence: object) -> PriceReference:
    cadence_key = _cadence_key(cadence)
    form_prices = _FORM_REFERENCES.get(taxonomy.form)
    if form_prices is not None:
        return PriceReference(
            family=taxonomy.family,
            form=taxonomy.form,
            cadence=cadence_key,
            reference_price_inr=float(form_prices[cadence_key]),
            source="form",
        )

    family_prices = _FAMILY_FALLBACKS.get(taxonomy.family, _FAMILY_FALLBACKS["general"])
    return PriceReference(
        family=taxonomy.family,
        form=taxonomy.form,
        cadence=cadence_key,
        reference_price_inr=float(family_prices[cadence_key]),
        source="family_fallback",
    )


def reference_price_for_taxonomy(taxonomy: ProductTaxonomy, cadence: object) -> float:
    return resolve_price_reference(taxonomy, cadence).reference_price_inr


def reference_price_for_family(family: str, cadence: object) -> float:
    cadence_key = _cadence_key(cadence)
    family_prices = _FAMILY_FALLBACKS.get(family, _FAMILY_FALLBACKS["general"])
    return float(family_prices[cadence_key])


def _cadence_key(cadence: object) -> str:
    raw = getattr(cadence, "value", cadence)
    key = str(raw)
    if key == "auto":
        return "one_time"
    if key not in {"one_time", "monthly", "yearly"}:
        raise ValueError(f"Unsupported billing cadence for price reference: {key}")
    return key
