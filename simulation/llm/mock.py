from __future__ import annotations

import json
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
        try:
            prompt = json.loads(user_prompt)
            dynamic = prompt.get("dynamic_conversation", {})
            sequence = list(dynamic.get("expected_speaker_sequence", ("A", "B")))
            semantic_turns = list(dynamic.get("fixed_semantic_messages", ()))
        except (TypeError, ValueError, json.JSONDecodeError):
            sequence = ["A", "B"]
            semantic_turns = []

        conversation: list[dict[str, str]] = []
        for index, speaker in enumerate(sequence):
            stance_band = (
                str(semantic_turns[index].get("stance_band", "neutral"))
                if index < len(semantic_turns) and isinstance(semantic_turns[index], dict)
                else "neutral"
            )
            if "negative" in stance_band:
                text = "That part gives me real concerns, and it makes me more cautious about buying the product."
            elif "positive" in stance_band:
                text = "That part works in the product's favor for me, although I would still weigh the other trade-offs."
            else:
                text = "I am still weighing that point and would want to consider it alongside the rest of the product."
            conversation.append({"speaker": str(speaker), "text": text})

        data: dict[str, Any] = {"conversation": conversation}
        return LLMJsonResponse(
            data=data,
            usage=LLMUsage(),
            latency_ms=0.0,
            model="mock",
        )
