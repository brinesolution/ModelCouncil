from __future__ import annotations

import json
import time
from typing import Any

import httpx

from simulation.audit.logger import RunAuditSink
from simulation.audit.redaction import redact_sensitive_strings
from simulation.llm.base import (
    LLMJsonResponse,
    LLMUsage,
    ProviderAuditContext,
    emit_provider_event,
)


class DeepSeekProvider:
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = "https://api.deepseek.com",
        model: str = "deepseek-v4-flash",
        thinking: str = "disabled",
        timeout_seconds: float = 45.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("DEEPSEEK_API_KEY is empty.")
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.thinking = thinking
        self.timeout_seconds = timeout_seconds
        self.transport = transport

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
        del json_schema  # DeepSeek currently uses JSON-object mode; post-validation remains authoritative.
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
        endpoint = f"{self.base_url}/chat/completions"
        emit_provider_event(
            audit,
            audit_context,
            "provider.http.request",
            {
                "provider": "deepseek",
                "method": "POST",
                "endpoint": endpoint,
                "headers": {
                    "Authorization": "[REDACTED]",
                    "Content-Type": "application/json",
                },
                "json": payload,
            },
        )

        started = time.perf_counter()
        response: httpx.Response | None = None
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout_seconds,
                transport=self.transport,
            ) as client:
                response = await client.post(endpoint, headers=headers, json=payload)
            latency_ms = (time.perf_counter() - started) * 1000
            response.raise_for_status()
            body = response.json()
        except httpx.HTTPStatusError as exc:
            latency_ms = (time.perf_counter() - started) * 1000
            emit_provider_event(
                audit,
                audit_context,
                "provider.http.error",
                {
                    "provider": "deepseek",
                    "endpoint": endpoint,
                    "status_code": exc.response.status_code,
                    "body": redact_sensitive_strings(
                        _response_body(exc.response), (self.api_key,)
                    ),
                    "latency_ms": latency_ms,
                    "error_type": type(exc).__name__,
                },
            )
            raise
        except httpx.RequestError as exc:
            latency_ms = (time.perf_counter() - started) * 1000
            emit_provider_event(
                audit,
                audit_context,
                "provider.http.error",
                {
                    "provider": "deepseek",
                    "endpoint": endpoint,
                    "status_code": None,
                    "latency_ms": latency_ms,
                    "error_type": type(exc).__name__,
                },
            )
            raise
        except (ValueError, json.JSONDecodeError) as exc:
            latency_ms = (time.perf_counter() - started) * 1000
            emit_provider_event(
                audit,
                audit_context,
                "provider.http.error",
                {
                    "provider": "deepseek",
                    "endpoint": endpoint,
                    "status_code": response.status_code if response is not None else None,
                    "body": redact_sensitive_strings(
                        _response_body(response), (self.api_key,)
                    ) if response is not None else None,
                    "latency_ms": latency_ms,
                    "error_type": type(exc).__name__,
                    "stage": "response_json",
                },
            )
            raise

        try:
            content = body["choices"][0]["message"]["content"]
            parsed = json.loads(content)
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            emit_provider_event(
                audit,
                audit_context,
                "provider.http.response",
                {
                    "provider": "deepseek",
                    "status_code": response.status_code,
                    "body": redact_sensitive_strings(body, (self.api_key,)),
                    "parsed_assistant_json": None,
                    "latency_ms": latency_ms,
                    "parse_error": type(exc).__name__,
                },
            )
            raise ValueError("DeepSeek returned an invalid structured response.") from exc

        if not isinstance(parsed, dict):
            emit_provider_event(
                audit,
                audit_context,
                "provider.http.response",
                {
                    "provider": "deepseek",
                    "status_code": response.status_code,
                    "body": redact_sensitive_strings(body, (self.api_key,)),
                    "parsed_assistant_json": parsed,
                    "latency_ms": latency_ms,
                    "parse_error": "non_object_json",
                },
            )
            raise ValueError("DeepSeek structured response must be a JSON object.")

        usage_body = body.get("usage") if isinstance(body, dict) else None
        if not isinstance(usage_body, dict):
            usage_body = {}
        usage = LLMUsage(
            prompt_tokens=int(usage_body.get("prompt_tokens", 0) or 0),
            prompt_cache_hit_tokens=int(
                usage_body.get("prompt_cache_hit_tokens", 0) or 0
            ),
            prompt_cache_miss_tokens=int(
                usage_body.get("prompt_cache_miss_tokens", 0) or 0
            ),
            completion_tokens=int(usage_body.get("completion_tokens", 0) or 0),
            total_tokens=int(usage_body.get("total_tokens", 0) or 0),
        )
        response_model = body.get("model", self.model) if isinstance(body, dict) else self.model
        emit_provider_event(
            audit,
            audit_context,
            "provider.http.response",
            {
                "provider": "deepseek",
                "status_code": response.status_code,
                "body": redact_sensitive_strings(body, (self.api_key,)),
                "parsed_assistant_json": parsed,
                "usage": usage,
                "model": str(response_model),
                "latency_ms": latency_ms,
            },
        )
        return LLMJsonResponse(
            data=parsed,
            usage=usage,
            latency_ms=latency_ms,
            model=str(response_model),
        )


def _response_body(response: httpx.Response) -> object:
    try:
        return response.json()
    except Exception:
        return response.text
