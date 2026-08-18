from simulation.audit.logger import JsonlRunAuditLogger
from simulation.audit.summary import write_markdown_summary


def test_markdown_summary_contains_required_debugging_sections(tmp_path):
    logger = JsonlRunAuditLogger(root=tmp_path, run_id="summary-run")
    logger.emit("run.started", {"run_kind": "normal"})
    logger.emit("population.agent_generated", {"source": "excel", "agent": {"agent_id": 1}}, agent_ids=[1])
    logger.emit(
        "round.completed",
        {
            "conversation_count": 7,
            "timeline": {
                "round_index": 1,
                "mean_opinion": 0.12,
                "mean_purchase_intent": 0.55,
                "positive_share": 0.3,
                "neutral_share": 0.6,
                "negative_share": 0.1,
            },
        },
        round_index=1,
    )
    logger.emit("language.render.completed", {"provider_model": "model-x", "usage": {"total_tokens": 50}})
    logger.emit("language.render.fallback", {"stage": "validation"})
    logger.emit("provider.http.error", {"provider": "deepseek", "status_code": 500})
    logger.emit("run.completed", {"status": "completed"})

    path = write_markdown_summary(
        logger,
        status="completed",
        product={"name": "Coach", "category": "Fitness Technology", "price": 500, "billing_cadence": "monthly"},
        configuration={
            "population_mode": "small",
            "dialogue_mode": "balanced",
            "rounds": 1,
            "seed": 42,
            "trait_source": "excel",
            "llm_provider": "deepseek",
            "llm_model": "model-x",
        },
        final_result={
            "population_size": 250,
            "conversation_count": 7,
            "final_mean_opinion": 0.12,
            "final_mean_purchase_intent": 0.55,
        },
        warnings=("Provider returned one HTTP error.",),
    )

    text = path.read_text(encoding="utf-8")
    for heading in (
        "# ModelCouncil Run Audit",
        "## Product",
        "## Configuration",
        "## Population",
        "## Language provider",
        "## Event counts",
        "## Round summary",
        "## Rendering / fallback summary",
        "## Final result",
        "## Failures / warnings",
    ):
        assert heading in text
    assert "summary-run" in text
    assert logger.jsonl_path.name in text
    assert "model-x" in text
    assert "language.render.fallback" in text
    assert "Provider returned one HTTP error." in text
    assert "canonical event-by-event trace" in text


def test_logger_keeps_only_bounded_summary_metadata_not_full_event_list(tmp_path):
    logger = JsonlRunAuditLogger(root=tmp_path)
    for round_index in range(1, 5):
        logger.emit(
            "round.completed",
            {"conversation_count": round_index, "timeline": {"round_index": round_index}},
            round_index=round_index,
        )
    for _ in range(10):
        logger.emit("language.render.fallback", {"stage": "validation"})

    assert not hasattr(logger, "events")
    assert len(logger.round_summaries) == 4
    assert logger.render_summary["fallback_count"] == 10
    assert logger.render_summary["completed_count"] == 0
    logger.close()
