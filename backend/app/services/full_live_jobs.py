from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import TYPE_CHECKING
from uuid import uuid4

from simulation.conversation.full_live_renderer import FullLiveProgress
from simulation.audit.logger import RunAuditSink

if TYPE_CHECKING:
    from backend.app.schemas.simulation import SimulationRunResponse


class FullLiveJobStatus(StrEnum):
    queued = "queued"
    simulating = "simulating"
    rendering = "rendering"
    cancelling = "cancelling"
    cancelled = "cancelled"
    completed = "completed"
    failed = "failed"


_TERMINAL_STATUSES = {
    FullLiveJobStatus.cancelled,
    FullLiveJobStatus.completed,
    FullLiveJobStatus.failed,
}


@dataclass(slots=True)
class FullLiveJobRecord:
    job_id: str
    product_name: str
    population_mode: str
    rounds: int
    seed: int
    estimated_upper_bound_conversations: int
    llm_provider: str
    llm_model: str
    status: FullLiveJobStatus = FullLiveJobStatus.queued
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    total_conversations: int | None = None
    processed_conversations: int = 0
    successful_renders: int = 0
    fallback_count: int = 0
    prompt_tokens: int = 0
    prompt_cache_hit_tokens: int = 0
    prompt_cache_miss_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cache_hit_ratio: float = 0.0
    average_latency_ms: float = 0.0
    max_latency_ms: float = 0.0
    estimated_cost_usd: float = 0.0
    provider_model: str | None = None
    error_message: str | None = None
    cancel_requested: bool = False
    audit_jsonl_path: str | None = None
    audit_summary_path: str | None = None
    result: SimulationRunResponse | None = None


class FullLiveJobManager:
    def __init__(self) -> None:
        self._jobs: dict[str, FullLiveJobRecord] = {}
        self._tasks: dict[str, asyncio.Task[None]] = {}
        self._cancel_events: dict[str, asyncio.Event] = {}
        self._audits: dict[str, RunAuditSink] = {}
        self._lock = asyncio.Lock()

    async def create(
        self,
        *,
        product_name: str,
        population_mode: str,
        rounds: int,
        seed: int,
        estimated_upper_bound_conversations: int,
        llm_provider: str,
        llm_model: str,
        audit_jsonl_path: str | None = None,
        audit_summary_path: str | None = None,
        audit: RunAuditSink | None = None,
    ) -> FullLiveJobRecord:
        job = FullLiveJobRecord(
            job_id=uuid4().hex,
            product_name=product_name,
            population_mode=population_mode,
            rounds=rounds,
            seed=seed,
            estimated_upper_bound_conversations=estimated_upper_bound_conversations,
            llm_provider=llm_provider,
            llm_model=llm_model,
            audit_jsonl_path=audit_jsonl_path,
            audit_summary_path=audit_summary_path,
        )
        async with self._lock:
            self._jobs[job.job_id] = job
            self._cancel_events[job.job_id] = asyncio.Event()
            if audit is not None:
                self._audits[job.job_id] = audit
        return job

    async def get(self, job_id: str) -> FullLiveJobRecord | None:
        async with self._lock:
            return self._jobs.get(job_id)

    async def set_task(self, job_id: str, task: asyncio.Task[None]) -> None:
        async with self._lock:
            if job_id not in self._jobs:
                raise KeyError(job_id)
            self._tasks[job_id] = task

    async def wait(self, job_id: str) -> FullLiveJobRecord | None:
        async with self._lock:
            job = self._jobs.get(job_id)
            task = self._tasks.get(job_id)
        if job is None:
            return None
        if task is not None:
            await task
        return await self.get(job_id)

    async def update_status(
        self,
        job_id: str,
        status: FullLiveJobStatus,
    ) -> FullLiveJobRecord:
        async with self._lock:
            job = self._require(job_id)
            job.status = status
            job.updated_at = datetime.now(timezone.utc)
            return job

    async def set_total_conversations(
        self,
        job_id: str,
        total_conversations: int,
    ) -> FullLiveJobRecord:
        async with self._lock:
            job = self._require(job_id)
            job.total_conversations = total_conversations
            job.updated_at = datetime.now(timezone.utc)
            return job

    async def update_progress(
        self,
        job_id: str,
        progress: FullLiveProgress,
    ) -> FullLiveJobRecord:
        async with self._lock:
            job = self._require(job_id)
            job.total_conversations = progress.total_conversations
            job.processed_conversations = progress.processed_conversations
            job.successful_renders = progress.successful_renders
            job.fallback_count = progress.fallback_count
            job.prompt_tokens = progress.prompt_tokens
            job.prompt_cache_hit_tokens = progress.prompt_cache_hit_tokens
            job.prompt_cache_miss_tokens = progress.prompt_cache_miss_tokens
            job.completion_tokens = progress.completion_tokens
            job.total_tokens = progress.total_tokens
            job.cache_hit_ratio = progress.cache_hit_ratio
            job.average_latency_ms = progress.average_latency_ms
            job.max_latency_ms = progress.max_latency_ms
            job.estimated_cost_usd = progress.estimated_cost_usd
            job.provider_model = progress.provider_model
            job.updated_at = datetime.now(timezone.utc)
            return job

    async def request_cancel(self, job_id: str) -> FullLiveJobRecord | None:
        async with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return None
            if job.status in _TERMINAL_STATUSES:
                return job
            job.cancel_requested = True
            job.status = FullLiveJobStatus.cancelling
            job.updated_at = datetime.now(timezone.utc)
            self._cancel_events[job_id].set()
            audit = self._audits.get(job_id)
            if audit is not None:
                audit.emit(
                    "run.cancel_requested",
                    {"status": "cancelling", "job_id": job_id},
                )
            return job

    def cancellation_check(self, job_id: str):
        event = self._cancel_events.get(job_id)
        if event is None:
            return lambda: True
        return event.is_set

    async def complete(
        self,
        job_id: str,
        result: SimulationRunResponse,
    ) -> FullLiveJobRecord:
        async with self._lock:
            job = self._require(job_id)
            job.result = result
            job.status = FullLiveJobStatus.completed
            job.updated_at = datetime.now(timezone.utc)
            return job

    async def mark_cancelled(self, job_id: str) -> FullLiveJobRecord:
        async with self._lock:
            job = self._require(job_id)
            job.status = FullLiveJobStatus.cancelled
            job.updated_at = datetime.now(timezone.utc)
            return job

    async def fail(self, job_id: str, error: Exception) -> FullLiveJobRecord:
        del error  # Never persist provider/internal exception text in browser-visible state.
        async with self._lock:
            job = self._require(job_id)
            job.status = FullLiveJobStatus.failed
            job.error_message = "Full Live job failed during backend processing."
            job.updated_at = datetime.now(timezone.utc)
            return job

    def _require(self, job_id: str) -> FullLiveJobRecord:
        try:
            return self._jobs[job_id]
        except KeyError as exc:
            raise KeyError(job_id) from exc


full_live_job_manager = FullLiveJobManager()
