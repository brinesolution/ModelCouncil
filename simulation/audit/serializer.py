from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Any, Mapping

try:
    import numpy as np
except Exception:  # pragma: no cover - NumPy is a runtime dependency today.
    np = None  # type: ignore[assignment]


def serialize_audit_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Enum):
        return serialize_audit_value(value.value)
    if isinstance(value, Path):
        return value.as_posix()
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if np is not None:
        if isinstance(value, np.generic):
            return value.item()
        if isinstance(value, np.ndarray):
            return [serialize_audit_value(item) for item in value.tolist()]
    if is_dataclass(value):
        return serialize_audit_value(asdict(value))
    if isinstance(value, Mapping):
        return {str(key): serialize_audit_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [serialize_audit_value(item) for item in value]
    if hasattr(value, "model_dump"):
        return serialize_audit_value(value.model_dump(mode="python"))
    if hasattr(value, "__dict__"):
        return serialize_audit_value(vars(value))
    return str(value)
