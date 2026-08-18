from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import math
import re
from typing import TYPE_CHECKING

from simulation.domain.agent import ConsumerAgent
from simulation.product.price_catalog import (
    reference_price_for_family,
    resolve_price_reference,
)
from simulation.product.taxonomy import resolve_product_taxonomy
from simulation.audit.logger import RunAuditSink

if TYPE_CHECKING:
    from simulation.product.knowledge import ProductKnowledge


class BillingCadence(StrEnum):
    auto = "auto"
    one_time = "one_time"
    monthly = "monthly"
    yearly = "yearly"


class PricePosition(StrEnum):
    inexpensive = "inexpensive"
    typical = "typical"
    premium = "premium"
    expensive = "expensive"


class PriceStanceBand(StrEnum):
    strongly_favorable = "strongly_favorable"
    mildly_favorable = "mildly_favorable"
    neutral_mixed = "neutral_mixed"
    mildly_unfavorable = "mildly_unfavorable"
    strongly_unfavorable = "strongly_unfavorable"


@dataclass(frozen=True, slots=True)
class ConsumerPriceContext:
    billing_cadence: BillingCadence
    reference_price_inr: float
    reference_ratio: float
    position: PricePosition
    affordability: float
    price_pressure: float
    stance: float
    stance_band: PriceStanceBand

    def with_stance(self, stance: float) -> "ConsumerPriceContext":
        resolved = _clip_opinion(stance)
        return ConsumerPriceContext(
            billing_cadence=self.billing_cadence,
            reference_price_inr=self.reference_price_inr,
            reference_ratio=self.reference_ratio,
            position=self.position,
            affordability=self.affordability,
            price_pressure=self.price_pressure,
            stance=resolved,
            stance_band=_stance_band(resolved),
        )


_ONE_TIME_PHRASES = (
    "one-time",
    "one time",
    "one-off",
    "one off",
    "lifetime purchase",
    "lifetime license",
    "no subscription",
    "no required subscription",
    "no recurring fee",
    "no recurring fees",
)
_MONTHLY_PHRASES = (
    "per month",
    "monthly",
    "monthly subscription",
    "monthly fee",
    "billed monthly",
)
_YEARLY_PHRASES = (
    "per year",
    "yearly",
    "annual",
    "annual subscription",
    "annual fee",
    "billed annually",
)
_SERVICE_HINTS = (
    "software",
    "saas",
    "subscription",
    "service",
    "platform",
    "mobile app",
    "web app",
    "fitness app",
    "ai coach",
    "digital coach",
)
_PHYSICAL_HINTS = (
    "electronics",
    "device",
    "hardware",
    "watch",
    "lamp",
    "gadget",
    "wearable",
    "appliance",
)


def resolve_billing_cadence(product: ProductKnowledge) -> BillingCadence:
    requested = BillingCadence(product.billing_cadence)
    if requested is not BillingCadence.auto:
        return requested

    source = " ".join((product.category, product.pitch, *product.features)).lower()

    # Explicit non-recurring language takes precedence over the substring
    # "subscription" inside phrases such as "no subscription".
    if _contains_any(source, _ONE_TIME_PHRASES):
        return BillingCadence.one_time
    if re.search(r"(?:₹|rs\.?|inr|\d)\s*[\d,.]*\s*/\s*month\b", source) or "/month" in source:
        return BillingCadence.monthly
    if re.search(r"(?:₹|rs\.?|inr|\d)\s*[\d,.]*\s*/\s*year\b", source) or "/year" in source:
        return BillingCadence.yearly
    if _contains_any(source, _MONTHLY_PHRASES):
        return BillingCadence.monthly
    if _contains_any(source, _YEARLY_PHRASES):
        return BillingCadence.yearly

    category_source = product.category.lower()
    if _contains_any(category_source, _PHYSICAL_HINTS):
        return BillingCadence.one_time
    if _contains_any(source, _SERVICE_HINTS):
        return BillingCadence.monthly
    return BillingCadence.one_time


def reference_price_for(category_family: str, cadence: BillingCadence) -> float:
    """Compatibility family-level price reference.

    New product execution resolves a taxonomy form through `build_consumer_price_context`;
    callers that only have a family retain the historical family fallback.
    """
    return reference_price_for_family(category_family, cadence)


def build_consumer_price_context(
    agent: ConsumerAgent,
    product: ProductKnowledge,
    *,
    category_family: str,
    need: float,
    audit: RunAuditSink | None = None,
) -> ConsumerPriceContext:
    cadence = resolve_billing_cadence(product)
    taxonomy = resolve_product_taxonomy(
        product.category,
        " ".join((product.pitch, *product.features)),
    )
    price_reference = resolve_price_reference(taxonomy, cadence)
    reference_price = price_reference.reference_price_inr
    if product.price is None or product.price <= 0:
        context = ConsumerPriceContext(
            billing_cadence=cadence,
            reference_price_inr=reference_price,
            reference_ratio=0.0,
            position=PricePosition.typical,
            affordability=0.75,
            price_pressure=0.0,
            stance=0.0,
            stance_band=PriceStanceBand.neutral_mixed,
        )
        if audit is not None:
            audit.emit(
                "consumer.price_context",
                {
                    "formula_version": "consumer-price-context-v2h",
                    "agent_id": agent.agent_id,
                    "inputs": {
                        "price": product.price,
                        "category_family": category_family,
                        "product_form": taxonomy.form,
                        "billing_cadence": cadence,
                        "reference_price_inr": reference_price,
                        "reference_source": price_reference.source,
                        "need": need,
                        "income_score": agent.income_score,
                        "price_sensitivity": agent.traits.price_sensitivity,
                    },
                    "components": {
                        "pressure": {},
                        "affordability": {},
                        "stance": {},
                    },
                    "pressure_raw": 0.0,
                    "affordability_raw": 0.75,
                    "stance_raw": 0.0,
                    "result": context,
                },
                agent_ids=[agent.agent_id],
            )
        return context

    ratio = max(float(product.price), 1.0) / max(reference_price, 1.0)
    amount_pressure = _clip01(0.45 + 0.32 * math.log(ratio))
    premium_penalty = min(0.28, max(0.0, ratio - 1.0) * 0.12)
    commitment_friction = {
        BillingCadence.one_time: 0.0,
        BillingCadence.monthly: 0.04,
        BillingCadence.yearly: 0.03,
        BillingCadence.auto: 0.0,
    }[cadence]
    pressure_components = {
        "amount_pressure": 0.72 * amount_pressure,
        "premium_penalty": premium_penalty,
        "base_pressure": 0.08,
        "price_sensitivity": 0.30 * (agent.traits.price_sensitivity - 0.50),
        "income": 0.22 * (0.50 - agent.income_score),
        "need": -0.20 * (_clip01(need) - 0.50),
        "commitment_friction": commitment_friction,
    }
    pressure_raw = sum(pressure_components.values())
    pressure = _clip01(pressure_raw)
    affordability_components = {
        "base_affordability": 0.74,
        "pressure": -0.62 * pressure,
        "income": 0.20 * agent.income_score,
        "need": 0.10 * _clip01(need),
        "price_sensitivity": -0.10 * agent.traits.price_sensitivity,
    }
    affordability_raw = sum(affordability_components.values())
    affordability = _clip01(affordability_raw)
    stance_components = {
        "base_stance": 0.75,
        "pressure": -1.60 * pressure,
        "affordability": 0.18 * (affordability - 0.50),
    }
    stance_raw = sum(stance_components.values())
    stance = _clip_opinion(stance_raw)
    context = ConsumerPriceContext(
        billing_cadence=cadence,
        reference_price_inr=reference_price,
        reference_ratio=float(ratio),
        position=_price_position(ratio),
        affordability=affordability,
        price_pressure=pressure,
        stance=stance,
        stance_band=_stance_band(stance),
    )
    if audit is not None:
        audit.emit(
            "consumer.price_context",
            {
                "formula_version": "consumer-price-context-v2h",
                "agent_id": agent.agent_id,
                "inputs": {
                    "price": product.price,
                    "category_family": category_family,
                    "product_form": taxonomy.form,
                    "billing_cadence": cadence,
                    "reference_price_inr": reference_price,
                    "reference_source": price_reference.source,
                    "reference_ratio": ratio,
                    "amount_pressure": amount_pressure,
                    "need": need,
                    "income_score": agent.income_score,
                    "price_sensitivity": agent.traits.price_sensitivity,
                },
                "components": {
                    "pressure": pressure_components,
                    "affordability": affordability_components,
                    "stance": stance_components,
                },
                "pressure_raw": pressure_raw,
                "affordability_raw": affordability_raw,
                "stance_raw": stance_raw,
                "result": context,
            },
            agent_ids=[agent.agent_id],
        )
    return context


def _price_position(ratio: float) -> PricePosition:
    if ratio <= 0.55:
        return PricePosition.inexpensive
    if ratio <= 1.25:
        return PricePosition.typical
    if ratio <= 2.0:
        return PricePosition.premium
    return PricePosition.expensive


def _stance_band(stance: float) -> PriceStanceBand:
    if stance > 0.45:
        return PriceStanceBand.strongly_favorable
    if stance > 0.12:
        return PriceStanceBand.mildly_favorable
    if stance >= -0.12:
        return PriceStanceBand.neutral_mixed
    if stance > -0.45:
        return PriceStanceBand.mildly_unfavorable
    return PriceStanceBand.strongly_unfavorable


def _clip01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _clip_opinion(value: float) -> float:
    return max(-1.0, min(1.0, float(value)))


def _contains_any(text: str, phrases: tuple[str, ...]) -> bool:
    compact = " ".join(text.replace("_", " ").split())
    return any(phrase in compact for phrase in phrases)
