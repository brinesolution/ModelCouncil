from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True, slots=True)
class TraitValue:
    key: str
    label: str
    probability: float
    attributes: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class TraitCategory:
    key: str
    values: tuple[TraitValue, ...]
    schema_version: str = "1.0"


@dataclass(frozen=True, slots=True)
class TraitCatalog:
    categories: dict[str, TraitCategory]

    def category(self, key: str) -> tuple[TraitValue, ...]:
        try:
            return self.categories[key].values
        except KeyError as exc:
            raise KeyError(f"Unknown trait category: {key}") from exc

    def has_category(self, key: str) -> bool:
        return key in self.categories


class TraitRepository(Protocol):
    def load_catalog(self) -> TraitCatalog:
        """Load and validate the complete trait catalog."""
