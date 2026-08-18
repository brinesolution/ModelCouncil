from dataclasses import dataclass, field

from simulation.product.pricing import BillingCadence


@dataclass(frozen=True, slots=True)
class Product:
    name: str
    pitch: str
    category: str = "General"
    price: float | None = None
    currency: str = "INR"
    billing_cadence: BillingCadence = BillingCadence.auto
    features: tuple[str, ...] = field(default_factory=tuple)
