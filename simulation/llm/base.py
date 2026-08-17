from __future__ import annotations

from typing import Any, Protocol


class LLMProvider(Protocol):
    async def generate_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 700,
    ) -> dict[str, Any]: ...
