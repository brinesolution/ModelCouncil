from __future__ import annotations

from typing import Any


class MockLLMProvider:
    """Deterministic provider for tests and offline development."""

    async def generate_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 700,
    ) -> dict[str, Any]:
        return {
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
