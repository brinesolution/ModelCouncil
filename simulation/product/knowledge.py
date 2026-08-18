from __future__ import annotations

from dataclasses import dataclass, field

from simulation.domain.product import Product
from simulation.product.pricing import BillingCadence, resolve_billing_cadence


@dataclass(frozen=True, slots=True)
class ProductKnowledge:
    name: str
    pitch: str
    category: str = "General"
    price: float | None = None
    currency: str = "INR"
    billing_cadence: BillingCadence = BillingCadence.auto
    features: tuple[str, ...] = field(default_factory=tuple)

    @property
    def resolved_billing_cadence(self) -> BillingCadence:
        return resolve_billing_cadence(self)

    @classmethod
    def from_product(cls, product: Product) -> "ProductKnowledge":
        return cls(
            name=product.name,
            pitch=product.pitch,
            category=product.category,
            price=product.price,
            currency=product.currency,
            billing_cadence=BillingCadence(product.billing_cadence),
            features=product.features,
        )
