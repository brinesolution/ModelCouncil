from __future__ import annotations

from typing import Any

from simulation.audit.logger import RunAuditSink
from simulation.llm.base import LLMJsonResponse, LLMUsage, ProviderAuditContext


class MockLLMProvider:
    """Deterministic provider for tests and offline development."""

    async def generate_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 700,
        json_schema: dict[str, Any] | None = None,
        audit: RunAuditSink | None = None,
        audit_context: ProviderAuditContext | None = None,
    ) -> LLMJsonResponse:
        del json_schema, audit, audit_context
        data: dict[str, Any] = {
            "conversation": [
                {"speaker": "A", "text": "The product sounds useful, but I would compare the price first."},
                {"speaker": "B", "text": "I agree on the price, though the convenience could still make it worthwhile."},
            ],
            "topics": {
                "price": -0.20,
                "usefulness": 0.35,
                "trust": 0.05,
            },
            "argument_strength": 0.45,
            "claims": [],
        }
        return LLMJsonResponse(
            data=data,
            usage=LLMUsage(),
            latency_ms=0.0,
            model="mock",
        )
