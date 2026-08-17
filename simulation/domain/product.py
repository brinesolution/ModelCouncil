from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class Product:
    name: str
    pitch: str
    category: str = "General"
    price: float | None = None
    currency: str = "INR"
    features: tuple[str, ...] = field(default_factory=tuple)
