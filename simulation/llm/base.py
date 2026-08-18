from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from simulation.audit.logger import RunAuditSink


@dataclass(frozen=True, slots=True)
class LLMUsage:
    prompt_tokens: int = 0
    prompt_cache_hit_tokens: int = 0
    prompt_cache_miss_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


@dataclass(frozen=True, slots=True)
class ProviderAuditContext:
    round_index: int | None = None
    conversation_id: str | None = None
    agent_ids: tuple[int, ...] = ()
    provider_request_id: str | None = None


@dataclass(frozen=True, slots=True)
class LLMJsonResponse:
    data: dict[str, Any]
    usage: LLMUsage
    latency_ms: float
    model: str


class LLMProvider(Protocol):
    async def generate_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 700,
        json_schema: dict[str, Any] | None = None,
        audit: RunAuditSink | None = None,
        audit_context: ProviderAuditContext | None = None,
    ) -> LLMJsonResponse: ...


def emit_provider_event(
    audit: RunAuditSink | None,
    audit_context: ProviderAuditContext | None,
    event_type: str,
    payload: dict[str, Any],
) -> None:
    if audit is None:
        return
    context = audit_context or ProviderAuditContext()
    audit.emit(
        event_type,
        payload,
        round_index=context.round_index,
        conversation_id=context.conversation_id,
        agent_ids=context.agent_ids or None,
        provider_request_id=context.provider_request_id,
    )
