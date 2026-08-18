from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from simulation.audit.logger import JsonlRunAuditLogger
from simulation.audit.serializer import serialize_audit_value


def write_markdown_summary(
    logger: JsonlRunAuditLogger,
    *,
    status: str,
    product: Mapping[str, Any] | None = None,
    configuration: Mapping[str, Any] | None = None,
    final_result: Mapping[str, Any] | None = None,
    warnings: tuple[str, ...] = (),
) -> Path:
    product_data = serialize_audit_value(product or {})
    configuration_data = serialize_audit_value(configuration or {})
    final_data = serialize_audit_value(final_result or {})
    finished = logger.finished_at.isoformat() if logger.finished_at is not None else "not closed yet"

    lines = [
        "# ModelCouncil Run Audit",
        "",
        f"- **Run ID:** `{logger.run_id}`",
        f"- **Status:** `{status}`",
        f"- **Started:** `{logger.started_at.isoformat()}`",
        f"- **Finished:** `{finished}`",
        f"- **Canonical JSONL:** `{logger.jsonl_path.name}`",
        f"- **Audit degraded:** `{logger.degraded}`",
        "",
        "## Product",
        "",
    ]
    _append_mapping(lines, product_data)

    lines.extend(["", "## Configuration", ""])
    _append_mapping(lines, configuration_data)

    lines.extend(["", "## Population", ""])
    population_size = _first_non_none(
        final_data.get("population_size"),
        _nested(final_data, "summary", "population_size"),
        logger.event_counts.get("population.agent_generated"),
    )
    lines.append(f"- **Generated agents:** `{population_size if population_size is not None else 'unknown'}`")
    lines.append(f"- **Trait source:** `{configuration_data.get('trait_source', 'unknown')}`")
    lines.append(f"- **Agent provenance events:** `{logger.event_counts.get('population.agent_generated', 0)}`")

    lines.extend(["", "## Language provider", ""])
    lines.append(f"- **Provider:** `{configuration_data.get('llm_provider') or 'deterministic / none'}`")
    lines.append(f"- **Requested model:** `{configuration_data.get('llm_model') or 'none'}`")
    lines.append(f"- **HTTP requests:** `{logger.event_counts.get('provider.http.request', 0)}`")
    lines.append(f"- **HTTP responses:** `{logger.event_counts.get('provider.http.response', 0)}`")
    lines.append(f"- **Provider errors:** `{logger.render_summary['provider_error_count']}`")

    lines.extend(["", "## Event counts", ""])
    for event, count in sorted(logger.event_counts.items()):
        lines.append(f"- `{event}`: {count}")
    if not logger.event_counts:
        lines.append("- No events recorded.")

    lines.extend(["", "## Round summary", ""])
    if logger.round_summaries:
        lines.extend(
            [
                "| Round | Conversations | Mean opinion | Mean purchase intent | Positive | Neutral | Negative |",
                "|---:|---:|---:|---:|---:|---:|---:|",
            ]
        )
        for item in logger.round_summaries:
            timeline = item.get("timeline") if isinstance(item, Mapping) else None
            timeline = timeline if isinstance(timeline, Mapping) else {}
            lines.append(
                "| {round} | {convos} | {opinion} | {purchase} | {positive} | {neutral} | {negative} |".format(
                    round=item.get("round", "?"),
                    convos=item.get("conversation_count", "?"),
                    opinion=_fmt(timeline.get("mean_opinion")),
                    purchase=_fmt(timeline.get("mean_purchase_intent")),
                    positive=_fmt(timeline.get("positive_share")),
                    neutral=_fmt(timeline.get("neutral_share")),
                    negative=_fmt(timeline.get("negative_share")),
                )
            )
    else:
        lines.append("No completed round summaries were recorded.")

    lines.extend(["", "## Rendering / fallback summary", ""])
    lines.append(f"- **Accepted live renders:** `{logger.render_summary['completed_count']}`")
    lines.append(f"- **Deterministic fallbacks:** `{logger.render_summary['fallback_count']}`")
    lines.append(f"- **Provider HTTP errors:** `{logger.render_summary['provider_error_count']}`")
    lines.append(f"- **Render requests:** `{logger.event_counts.get('language.render.request', 0)}`")
    lines.append(f"- **Validation failures:** `{logger.event_counts.get('language.render.validation_failed', 0)}`")

    lines.extend(["", "## Final result", ""])
    if final_data:
        _append_mapping(lines, final_data)
    else:
        lines.append("No completed final result was available.")

    lines.extend(["", "## Failures / warnings", ""])
    if warnings:
        lines.extend(f"- {warning}" for warning in warnings)
    elif logger.degraded:
        lines.append("- The audit writer entered degraded mode; inspect the canonical JSONL for the last valid event.")
    else:
        lines.append("- None recorded in the summary.")

    lines.extend(
        [
            "",
            "> The JSONL file is the canonical event-by-event trace. This Markdown file is only a human-readable summary/index.",
            "",
        ]
    )
    logger.summary_path.write_text("\n".join(lines), encoding="utf-8")
    return logger.summary_path


def _append_mapping(lines: list[str], data: Mapping[str, Any]) -> None:
    if not data:
        lines.append("- No data recorded.")
        return
    for key, value in data.items():
        lines.append(f"- **{key}:** `{_display(value)}`")


def _display(value: Any) -> str:
    if isinstance(value, (dict, list)):
        return str(value)
    return str(value)


def _nested(data: Mapping[str, Any], first: str, second: str) -> Any:
    child = data.get(first)
    if isinstance(child, Mapping):
        return child.get(second)
    return None


def _first_non_none(*values: Any) -> Any:
    return next((value for value in values if value is not None), None)


def _fmt(value: Any) -> str:
    if isinstance(value, (int, float)):
        return f"{float(value):.4f}"
    return "—"
