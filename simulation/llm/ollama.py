from __future__ import annotations

import json
import time
from typing import Any

import httpx

from simulation.audit.logger import RunAuditSink
from simulation.llm.base import (
    LLMJsonResponse,
    LLMUsage,
    ProviderAuditContext,
    emit_provider_event,
)


class OllamaProvider:
    def __init__(
        self,
        *,
        model: str,
        base_url: str = "http://127.0.0.1:11434",
        timeout_seconds: float = 120.0,
        context_window: int = 2048,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        if not model.strip():
            raise ValueError("Ollama model is empty.")
        self.model = model.strip()
        self.base_url = base_url.rstrip("/")
        if context_window < 512:
            raise ValueError("Ollama context window must be at least 512 tokens.")
        self.timeout_seconds = timeout_seconds
        self.context_window = context_window
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
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "format": json_schema or "json",
            "options": {
                "temperature": 0.65,
                "num_predict": max_tokens,
                "num_ctx": self.context_window,
            },
        }
        endpoint = f"{self.base_url}/api/chat"
        emit_provider_event(
            audit,
            audit_context,
            "provider.http.request",
            {
                "provider": "ollama",
                "method": "POST",
                "endpoint": endpoint,
                "headers": {"Content-Type": "application/json"},
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
                response = await client.post(endpoint, json=payload)
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
                    "provider": "ollama",
                    "endpoint": endpoint,
                    "status_code": exc.response.status_code,
                    "body": _response_body(exc.response),
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
                    "provider": "ollama",
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
                    "provider": "ollama",
                    "endpoint": endpoint,
                    "status_code": response.status_code if response is not None else None,
                    "body": _response_body(response) if response is not None else None,
                    "latency_ms": latency_ms,
                    "error_type": type(exc).__name__,
                    "stage": "response_json",
                },
            )
            raise

        try:
            content = body["message"]["content"]
            parsed = json.loads(content)
        except (KeyError, TypeError, json.JSONDecodeError) as exc:
            emit_provider_event(
                audit,
                audit_context,
                "provider.http.response",
                {
                    "provider": "ollama",
                    "status_code": response.status_code,
                    "body": body,
                    "parsed_assistant_json": None,
                    "latency_ms": latency_ms,
                    "parse_error": type(exc).__name__,
                },
            )
            raise ValueError("Ollama returned an invalid structured response.") from exc

        if not isinstance(parsed, dict):
            emit_provider_event(
                audit,
                audit_context,
                "provider.http.response",
                {
                    "provider": "ollama",
                    "status_code": response.status_code,
                    "body": body,
                    "parsed_assistant_json": parsed,
                    "latency_ms": latency_ms,
                    "parse_error": "non_object_json",
                },
            )
            raise ValueError("Ollama structured response must be a JSON object.")

        prompt_tokens = int(body.get("prompt_eval_count", 0) or 0)
        completion_tokens = int(body.get("eval_count", 0) or 0)
        usage = LLMUsage(
            prompt_tokens=prompt_tokens,
            prompt_cache_hit_tokens=0,
            prompt_cache_miss_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
        )
        response_model = str(body.get("model", self.model))
        emit_provider_event(
            audit,
            audit_context,
            "provider.http.response",
            {
                "provider": "ollama",
                "status_code": response.status_code,
                "body": body,
                "parsed_assistant_json": parsed,
                "usage": usage,
                "model": response_model,
                "latency_ms": latency_ms,
            },
        )
        return LLMJsonResponse(
            data=parsed,
            usage=usage,
            latency_ms=latency_ms,
            model=response_model,
        )


def _response_body(response: httpx.Response) -> object:
    try:
        return response.json()
    except Exception:
        return response.text
