from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from simulation.audit.events import PRIVATE_REASONING_REDACTION, SECRET_REDACTION
from simulation.audit.serializer import serialize_audit_value

_SECRET_KEYS = {
    "authorization",
    "api_key",
    "apikey",
    "token",
    "access_token",
    "refresh_token",
    "secret",
    "client_secret",
    "password",
    "cookie",
    "cookies",
    "set_cookie",
}
_PRIVATE_REASONING_KEYS = {
    "reasoning_content",
    "chain_of_thought",
    "chainofthought",
    "hidden_reasoning",
    "private_reasoning",
    "thinking",
}


def _normalize_key(key: object) -> str:
    return str(key).strip().lower().replace("-", "_")


def redact_audit_value(value: Any) -> Any:
    serialized = serialize_audit_value(value)
    return _redact_serialized(serialized)


def redact_sensitive_strings(value: Any, sensitive_values: Sequence[str]) -> Any:
    serialized = serialize_audit_value(value)
    secrets = tuple(secret for secret in sensitive_values if isinstance(secret, str) and secret)
    return _redact_exact_strings(serialized, secrets)


def _redact_exact_strings(value: Any, secrets: tuple[str, ...]) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _redact_exact_strings(item, secrets) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_redact_exact_strings(item, secrets) for item in value]
    if isinstance(value, str):
        result = value
        for secret in secrets:
            result = result.replace(secret, SECRET_REDACTION)
        return result
    return value


def _redact_serialized(value: Any) -> Any:
    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for raw_key, item in value.items():
            key = str(raw_key)
            normalized = _normalize_key(key)
            if normalized in _SECRET_KEYS:
                result[key] = SECRET_REDACTION
            elif normalized in _PRIVATE_REASONING_KEYS:
                result[key] = PRIVATE_REASONING_REDACTION
            else:
                result[key] = _redact_serialized(item)
        return result
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_redact_serialized(item) for item in value]
    return value
