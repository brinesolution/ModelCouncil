from __future__ import annotations

import json
from typing import Any

import httpx


class DeepSeekProvider:
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = "https://api.deepseek.com",
        model: str = "deepseek-v4-flash",
        thinking: str = "disabled",
        timeout_seconds: float = 45.0,
    ) -> None:
        if not api_key:
            raise ValueError("DEEPSEEK_API_KEY is empty.")
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.thinking = thinking
        self.timeout_seconds = timeout_seconds

    async def generate_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 700,
    ) -> dict[str, Any]:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "thinking": {"type": self.thinking},
            "response_format": {"type": "json_object"},
            "max_tokens": max_tokens,
            "temperature": 0.65,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            body = response.json()

        try:
            content = body["choices"][0]["message"]["content"]
            parsed = json.loads(content)
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise ValueError("DeepSeek returned an invalid structured response.") from exc

        if not isinstance(parsed, dict):
            raise ValueError("DeepSeek structured response must be a JSON object.")
        return parsed
