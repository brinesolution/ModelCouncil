from __future__ import annotations

import platform
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping

from simulation.audit.logger import JsonlRunAuditLogger
from simulation.audit.serializer import serialize_audit_value
from simulation.audit.summary import write_markdown_summary
from backend.app.schemas.simulation import SimulationPreviewRequest
from backend.app.services.simulation_config_service import (
    estimate_conversation_upper_bound,
    resolve_effective_preset,
)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
AUDIT_ROOT = PROJECT_ROOT / "logs" / "model-runs"


def _payload_dict(value: Any) -> dict[str, Any]:
    if hasattr(value, "model_dump"):
        return serialize_audit_value(value.model_dump(mode="python"))
    if isinstance(value, Mapping):
        return serialize_audit_value(dict(value))
    return {"value": serialize_audit_value(value)}


def _typed_request(request: Any) -> SimulationPreviewRequest:
    if isinstance(request, SimulationPreviewRequest):
        return request
    return SimulationPreviewRequest.model_validate(request)


def _effective_configuration(request: Any) -> dict[str, Any]:
    typed_request = _typed_request(request)
    preset = resolve_effective_preset(typed_request)
    return {
        "advanced_config_enabled": typed_request.advanced_config is not None,
        "effective_preset": serialize_audit_value(preset),
        "workload_upper_bound": estimate_conversation_upper_bound(typed_request),
    }


def create_run_audit(
    request: Any,
    *,
    run_kind: str,
    provider_id: str | None = None,
    model_id: str | None = None,
    root: Path | None = None,
) -> JsonlRunAuditLogger:
    logger = JsonlRunAuditLogger(root=root or AUDIT_ROOT)
    request_payload = _payload_dict(request)
    effective_configuration = _effective_configuration(request)
    logger.emit(
        "run.started",
        {
            "run_kind": run_kind,
            "request": request_payload,
            "provider_id": provider_id,
            "model_id": model_id,
            "runtime": _runtime_metadata(),
            "git": _git_metadata(),
        },
    )
    logger.emit(
        "run.configuration",
        {
            "run_kind": run_kind,
            "population_mode": request_payload.get("population_mode"),
            "dialogue_mode": request_payload.get("dialogue_mode"),
            "rounds": request_payload.get("rounds"),
            "seed": request_payload.get("seed"),
            "provider_id": provider_id,
            "model_id": model_id,
            **effective_configuration,
        },
    )
    product = request_payload.get("product")
    if isinstance(product, Mapping):
        logger.emit("product.input", dict(product))
    return logger


def create_run_audit_from_payload(
    payload: Mapping[str, Any],
    *,
    run_kind: str,
    provider_id: str | None = None,
    model_id: str | None = None,
    root: Path | None = None,
) -> JsonlRunAuditLogger:
    return create_run_audit(
        dict(payload),
        run_kind=run_kind,
        provider_id=provider_id,
        model_id=model_id,
        root=root,
    )


def emit_run_completed(logger: JsonlRunAuditLogger, result: Any) -> None:
    payload = _payload_dict(result)
    logger.emit(
        "run.completed",
        {
            "status": "completed",
            "summary": payload.get("summary"),
            "analytics": payload.get("analytics"),
            "dialogue_stats": payload.get("dialogue_stats"),
        },
    )


def emit_run_failed(logger: JsonlRunAuditLogger, exc: BaseException) -> None:
    logger.emit(
        "run.failed",
        {
            "status": "failed",
            "error_type": type(exc).__name__,
            "error_message": "Run failed during backend processing.",
        },
    )


def emit_run_cancel_requested(logger: JsonlRunAuditLogger) -> None:
    logger.emit("run.cancel_requested", {"status": "cancelling"})


def emit_run_cancelled(logger: JsonlRunAuditLogger) -> None:
    logger.emit("run.cancelled", {"status": "cancelled"})


def finalize_run_audit(
    logger: JsonlRunAuditLogger,
    *,
    status: str,
    request: Any,
    final_result: Any | None = None,
    warnings: tuple[str, ...] = (),
) -> None:
    request_payload = _payload_dict(request)
    product = request_payload.get("product") if isinstance(request_payload.get("product"), Mapping) else {}
    result_payload = _payload_dict(final_result) if final_result is not None else {}
    configuration = {
        "population_mode": request_payload.get("population_mode"),
        "dialogue_mode": request_payload.get("dialogue_mode"),
        "rounds": request_payload.get("rounds"),
        "seed": request_payload.get("seed"),
        "trait_source": result_payload.get("trait_source"),
        "llm_provider": result_payload.get("llm_provider") or request_payload.get("llm_provider"),
        "llm_model": result_payload.get("llm_model") or request_payload.get("llm_model"),
        **_effective_configuration(request),
    }
    write_markdown_summary(
        logger,
        status=status,
        product=product,
        configuration=configuration,
        final_result={
            "summary": result_payload.get("summary"),
            "dialogue_stats": result_payload.get("dialogue_stats"),
        }
        if result_payload
        else {},
        warnings=warnings,
    )
    logger.emit(
        "run.summary_written",
        {"summary_path": logger.summary_path.name, "status": status},
    )
    logger.close()


def _runtime_metadata() -> dict[str, Any]:
    return {
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "implementation": platform.python_implementation(),
    }


def _git_metadata() -> dict[str, Any]:
    def run(*args: str) -> str | None:
        try:
            result = subprocess.run(
                ["git", *args],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                timeout=2,
                check=False,
            )
        except Exception:
            return None
        if result.returncode != 0:
            return None
        return result.stdout.strip()

    status = run("status", "--porcelain")
    return {
        "revision": run("rev-parse", "HEAD"),
        "branch": run("branch", "--show-current"),
        "dirty": bool(status) if status is not None else None,
    }
