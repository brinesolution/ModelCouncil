from __future__ import annotations

from dataclasses import dataclass, field

from simulation.domain.product import Product


@dataclass(frozen=True, slots=True)
class ProductKnowledge:
    name: str
    pitch: str
    category: str = "General"
    price: float | None = None
    currency: str = "INR"
    features: tuple[str, ...] = field(default_factory=tuple)

    @classmethod
    def from_product(cls, product: Product) -> "ProductKnowledge":
        return cls(
            name=product.name,
            pitch=product.pitch,
            category=product.category,
            price=product.price,
            currency=product.currency,
            features=product.features,
        )
