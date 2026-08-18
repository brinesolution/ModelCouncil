from simulation.audit.logger import JsonlRunAuditLogger, NullRunAuditLogger
from simulation.engine import SimulationConfig, SimulationEngine
from simulation.population.generator import generate_population
from simulation.product.knowledge import ProductKnowledge


def test_large_trace_is_streamed_without_in_memory_event_list(tmp_path):
    logger = JsonlRunAuditLogger(root=tmp_path)
    count = 20_000
    for index in range(count):
        logger.emit("stress.compact", {"index": index})
    logger.close()

    assert not hasattr(logger, "events")
    with logger.jsonl_path.open("r", encoding="utf-8") as handle:
        assert sum(1 for _ in handle) == count


def test_mid_run_writer_failure_degrades_logger_without_changing_simulation_result(tmp_path, monkeypatch):
    product = ProductKnowledge(
        name="Coach",
        category="Fitness Technology",
        pitch="Personalized coaching with a monthly subscription.",
        price=500,
        billing_cadence="monthly",
    )
    population = generate_population(30, seed=115)
    config = SimulationConfig(rounds=3, seed=115, k=5, initiator_rate=0.3)
    expected = SimulationEngine().run(product, population, config, audit=NullRunAuditLogger())

    logger = JsonlRunAuditLogger(root=tmp_path)
    original_write = logger._write_event
    calls = 0

    def flaky_write(event):
        nonlocal calls
        calls += 1
        if calls >= 2:
            raise OSError("simulated audit disk failure")
        return original_write(event)

    monkeypatch.setattr(logger, "_write_event", flaky_write)
    actual = SimulationEngine().run(product, population, config, audit=logger)
    logger.close()

    assert logger.degraded is True
    assert actual.timeline == expected.timeline
    assert actual.population == expected.population
    assert [entry.pair for entry in actual.conversations] == [entry.pair for entry in expected.conversations]
    assert [entry.result for entry in actual.conversations] == [entry.result for entry in expected.conversations]
    assert actual.checkpoints == expected.checkpoints
