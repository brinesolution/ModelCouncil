import json
from concurrent.futures import ThreadPoolExecutor

from simulation.audit.logger import JsonlRunAuditLogger, MemoryRunAuditLogger


def test_jsonl_writer_serializes_concurrent_emitters_without_corruption(tmp_path):
    logger = JsonlRunAuditLogger(root=tmp_path, run_id="concurrent")
    workers = 16
    per_worker = 125

    def emit_worker(worker_id: int) -> None:
        for index in range(per_worker):
            logger.emit(
                "stress.event",
                {"worker": worker_id, "index": index},
                round_index=(index % 5) + 1,
                provider_request_id=f"w{worker_id}-{index}",
            )

    with ThreadPoolExecutor(max_workers=workers) as pool:
        list(pool.map(emit_worker, range(workers)))
    logger.close()

    lines = logger.jsonl_path.read_text(encoding="utf-8").splitlines()
    events = [json.loads(line) for line in lines]
    expected = workers * per_worker
    assert len(events) == expected
    sequences = [event["sequence"] for event in events]
    assert sequences == list(range(1, expected + 1))
    assert len({event["provider_request_id"] for event in events}) == expected
    assert all(event["event"] == "stress.event" for event in events)


def test_cancel_request_event_can_be_emitted_safely_from_manager_sink():
    audit = MemoryRunAuditLogger(run_id="cancel")
    audit.emit("run.cancel_requested", {"status": "cancelling"})
    assert audit.events[-1]["event"] == "run.cancel_requested"
