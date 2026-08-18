import json
import re
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from pathlib import Path

import numpy as np

from simulation.audit.logger import JsonlRunAuditLogger, MemoryRunAuditLogger, NullRunAuditLogger
from simulation.audit.serializer import serialize_audit_value


_FILENAME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}-\d{6}_[A-Za-z]+\.jsonl$")


class ExampleEnum(StrEnum):
    value = "value"


@dataclass(frozen=True)
class ExampleDataclass:
    amount: float
    state: ExampleEnum


def test_serializer_handles_domain_friendly_values():
    value = {
        "path": Path("data/example.xlsx"),
        "time": datetime.now().astimezone(),
        "enum": ExampleEnum.value,
        "data": ExampleDataclass(amount=np.float64(1.25), state=ExampleEnum.value),
        "array": np.asarray([1, 2, 3], dtype=np.int64),
    }

    result = serialize_audit_value(value)

    assert result["path"] == "data/example.xlsx"
    assert "+" in result["time"] or result["time"].endswith("Z")
    assert result["enum"] == "value"
    assert result["data"] == {"amount": 1.25, "state": "value"}
    assert result["array"] == [1, 2, 3]


def test_jsonl_logger_creates_timestamped_file_and_ordered_valid_events(tmp_path):
    logger = JsonlRunAuditLogger(root=tmp_path)

    assert _FILENAME_RE.match(logger.jsonl_path.name)
    assert logger.summary_path.suffix == ".md"
    assert logger.summary_path.stem == logger.jsonl_path.stem

    logger.emit("run.started", {"value": 1})
    logger.emit(
        "conversation.semantic_message",
        {"topic": "price"},
        round_index=2,
        conversation_id="r2-a1-a2",
        agent_ids=[1, 2],
        provider_request_id="req-7",
    )
    logger.emit("run.completed", {"status": "completed"})
    logger.close()
    logger.close()

    lines = logger.jsonl_path.read_text(encoding="utf-8").splitlines()
    events = [json.loads(line) for line in lines]

    assert [event["sequence"] for event in events] == [1, 2, 3]
    assert [event["event"] for event in events] == [
        "run.started",
        "conversation.semantic_message",
        "run.completed",
    ]
    assert all(event["schema_version"] == "modelcouncil-run-audit-v1" for event in events)
    assert all(event["run_id"] == logger.run_id for event in events)
    assert all(datetime.fromisoformat(event["timestamp"]).tzinfo is not None for event in events)
    assert events[1]["round"] == 2
    assert events[1]["conversation_id"] == "r2-a1-a2"
    assert events[1]["agent_ids"] == [1, 2]
    assert events[1]["provider_request_id"] == "req-7"
    assert logger.event_counts["conversation.semantic_message"] == 1


def test_jsonl_logger_uses_unique_microsecond_stems(tmp_path):
    first = JsonlRunAuditLogger(root=tmp_path)
    second = JsonlRunAuditLogger(root=tmp_path)
    try:
        assert first.jsonl_path != second.jsonl_path
    finally:
        first.close()
        second.close()


def test_jsonl_logger_redacts_before_writing(tmp_path):
    logger = JsonlRunAuditLogger(root=tmp_path)
    logger.emit(
        "provider.http.request",
        {"headers": {"Authorization": "Bearer secret-value"}, "api_key": "key-value"},
    )
    logger.close()

    raw = logger.jsonl_path.read_text(encoding="utf-8")
    assert "secret-value" not in raw
    assert "key-value" not in raw
    assert raw.count("[REDACTED]") == 2


def test_memory_and_null_loggers_have_stable_protocol_behavior():
    memory = MemoryRunAuditLogger(run_id="memory-run")
    null = NullRunAuditLogger()

    memory.emit("run.started", {"a": 1})
    null.emit("run.started", {"a": 1})

    assert len(memory.events) == 1
    assert memory.events[0]["sequence"] == 1
    assert memory.events[0]["run_id"] == "memory-run"
    assert null.event_counts == {}
    memory.close()
    null.close()
