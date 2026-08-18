from __future__ import annotations

import json
import threading
from collections import Counter
from collections.abc import Mapping, Sequence
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol
from uuid import uuid4

from simulation.audit.events import AUDIT_SCHEMA_VERSION
from simulation.audit.redaction import redact_audit_value


class RunAuditSink(Protocol):
    run_id: str

    def emit(
        self,
        event_type: str,
        payload: Mapping[str, Any],
        *,
        round_index: int | None = None,
        conversation_id: str | None = None,
        agent_ids: Sequence[int] | None = None,
        provider_request_id: str | None = None,
    ) -> None: ...

    def close(self) -> None: ...


class NullRunAuditLogger:
    run_id = "null"
    event_counts: dict[str, int] = {}
    degraded = False
    last_error: str | None = None

    def emit(
        self,
        event_type: str,
        payload: Mapping[str, Any],
        *,
        round_index: int | None = None,
        conversation_id: str | None = None,
        agent_ids: Sequence[int] | None = None,
        provider_request_id: str | None = None,
    ) -> None:
        return None

    def close(self) -> None:
        return None


class MemoryRunAuditLogger:
    def __init__(self, *, run_id: str | None = None) -> None:
        self.run_id = run_id or uuid4().hex
        self.events: list[dict[str, Any]] = []
        self.event_counts: Counter[str] = Counter()
        self.degraded = False
        self.last_error: str | None = None
        self._sequence = 0
        self._closed = False
        self._lock = threading.RLock()

    def emit(
        self,
        event_type: str,
        payload: Mapping[str, Any],
        *,
        round_index: int | None = None,
        conversation_id: str | None = None,
        agent_ids: Sequence[int] | None = None,
        provider_request_id: str | None = None,
    ) -> None:
        with self._lock:
            if self._closed:
                return
            self._sequence += 1
            event = _build_envelope(
                sequence=self._sequence,
                run_id=self.run_id,
                event_type=event_type,
                payload=payload,
                round_index=round_index,
                conversation_id=conversation_id,
                agent_ids=agent_ids,
                provider_request_id=provider_request_id,
            )
            self.events.append(event)
            self.event_counts[event_type] += 1

    def close(self) -> None:
        with self._lock:
            self._closed = True


class JsonlRunAuditLogger:
    def __init__(self, *, root: Path | str, run_id: str | None = None) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.run_id = run_id or uuid4().hex
        self._lock = threading.RLock()
        self._sequence = 0
        self._closed = False
        self.degraded = False
        self.last_error: str | None = None
        self.event_counts: Counter[str] = Counter()
        self.round_summaries: list[dict[str, Any]] = []
        self.render_summary: dict[str, int] = {
            "completed_count": 0,
            "fallback_count": 0,
            "provider_error_count": 0,
        }
        self.started_at = datetime.now().astimezone()
        self.finished_at: datetime | None = None
        self._stem = self._unique_stem(self.started_at)
        self.jsonl_path = self.root / f"{self._stem}.jsonl"
        self.summary_path = self.root / f"{self._stem}.md"
        self._handle = self.jsonl_path.open("x", encoding="utf-8", newline="\n")

    def _unique_stem(self, started_at: datetime) -> str:
        candidate_time = started_at
        while True:
            stem = candidate_time.strftime("%Y-%m-%d_%H-%M-%S-%f_%A")
            if not (self.root / f"{stem}.jsonl").exists() and not (self.root / f"{stem}.md").exists():
                return stem
            candidate_time = datetime.now().astimezone()

    def emit(
        self,
        event_type: str,
        payload: Mapping[str, Any],
        *,
        round_index: int | None = None,
        conversation_id: str | None = None,
        agent_ids: Sequence[int] | None = None,
        provider_request_id: str | None = None,
    ) -> None:
        with self._lock:
            if self._closed or self.degraded:
                return
            try:
                self._sequence += 1
                event = _build_envelope(
                    sequence=self._sequence,
                    run_id=self.run_id,
                    event_type=event_type,
                    payload=payload,
                    round_index=round_index,
                    conversation_id=conversation_id,
                    agent_ids=agent_ids,
                    provider_request_id=provider_request_id,
                )
                self._write_event(event)
                self.event_counts[event_type] += 1
                self._record_summary_metadata(event)
            except Exception as exc:
                failed_sequence = self._sequence
                try:
                    safe_error = {
                        "schema_version": AUDIT_SCHEMA_VERSION,
                        "sequence": failed_sequence,
                        "timestamp": datetime.now().astimezone().isoformat(),
                        "event": "audit.serialization_error",
                        "run_id": self.run_id,
                        "payload": {
                            "original_event": str(event_type),
                            "error_type": type(exc).__name__,
                            "error_message": "Audit event serialization/write failed.",
                        },
                    }
                    self._write_event(safe_error)
                    self.event_counts["audit.serialization_error"] += 1
                except Exception as write_exc:
                    self.degraded = True
                    self.last_error = f"{type(write_exc).__name__}: {write_exc}"

    def _write_event(self, event: Mapping[str, Any]) -> None:
        line = json.dumps(event, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
        self._handle.write(line + "\n")
        self._handle.flush()

    def _record_summary_metadata(self, event: Mapping[str, Any]) -> None:
        event_type = str(event.get("event", ""))
        payload = event.get("payload")
        if event_type == "round.completed" and isinstance(payload, Mapping):
            self.round_summaries.append(
                {
                    "round": event.get("round"),
                    "conversation_count": payload.get("conversation_count"),
                    "timeline": payload.get("timeline"),
                }
            )
        elif event_type == "language.render.completed":
            self.render_summary["completed_count"] += 1
        elif event_type == "language.render.fallback":
            self.render_summary["fallback_count"] += 1
        elif event_type == "provider.http.error":
            self.render_summary["provider_error_count"] += 1

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            self.finished_at = datetime.now().astimezone()
            try:
                self._handle.flush()
            finally:
                self._handle.close()
                self._closed = True


def _build_envelope(
    *,
    sequence: int,
    run_id: str,
    event_type: str,
    payload: Mapping[str, Any],
    round_index: int | None,
    conversation_id: str | None,
    agent_ids: Sequence[int] | None,
    provider_request_id: str | None,
) -> dict[str, Any]:
    event: dict[str, Any] = {
        "schema_version": AUDIT_SCHEMA_VERSION,
        "sequence": sequence,
        "timestamp": datetime.now().astimezone().isoformat(),
        "event": str(event_type),
        "run_id": run_id,
        "payload": redact_audit_value(dict(payload)),
    }
    if round_index is not None:
        event["round"] = int(round_index)
    if conversation_id is not None:
        event["conversation_id"] = str(conversation_id)
    if agent_ids is not None:
        event["agent_ids"] = [int(agent_id) for agent_id in agent_ids]
    if provider_request_id is not None:
        event["provider_request_id"] = str(provider_request_id)
    return event
