from __future__ import annotations

import asyncio

from backend.app.core.config import get_settings
from backend.app.schemas.simulation import DialogueMode, FullLiveSimulationRequest, SimulationPreviewRequest
from backend.app.services.full_live_jobs import (
    FullLiveJobManager,
    FullLiveJobRecord,
    FullLiveJobStatus,
    full_live_job_manager,
)
from backend.app.services.llm_provider_factory import (
    LLMProviderResolutionError,
    ResolvedLLMProvider,
    resolve_llm_provider,
)
from backend.app.services.simulation_service import (
    _run_core_simulation,
    build_run_response,
)
from backend.app.services.run_audit_service import (
    create_run_audit,
    emit_run_cancelled,
    emit_run_completed,
    emit_run_failed,
    finalize_run_audit,
)
from backend.app.services.simulation_config_service import estimate_conversation_upper_bound
from simulation.conversation.full_live_renderer import render_all_conversations_live
from simulation.conversation.ledger import ProductLanguageContext


class FullLiveConfigurationError(RuntimeError):
    pass


def estimate_upper_bound_conversations(request: SimulationPreviewRequest) -> int:
    return estimate_conversation_upper_bound(request)


async def start_full_live_job(
    request: FullLiveSimulationRequest,
    *,
    manager: FullLiveJobManager = full_live_job_manager,
) -> FullLiveJobRecord:
    if request.dialogue_mode is not DialogueMode.full_live:
        raise FullLiveConfigurationError(
            "Full Live jobs require dialogue_mode=full_live."
        )

    settings = get_settings()
    try:
        resolved = await resolve_llm_provider(
            request.llm_provider,
            request.llm_model,
            settings=settings,
        )
    except LLMProviderResolutionError as exc:
        raise FullLiveConfigurationError(str(exc)) from exc

    audit = create_run_audit(
        request,
        run_kind="full_live",
        provider_id=resolved.provider_id,
        model_id=resolved.model_id,
    )
    job = await manager.create(
        product_name=request.product.name,
        population_mode=request.population_mode.value,
        rounds=request.rounds,
        seed=request.seed,
        estimated_upper_bound_conversations=estimate_upper_bound_conversations(request),
        llm_provider=resolved.provider_id,
        llm_model=resolved.model_id,
        audit_jsonl_path=str(audit.jsonl_path),
        audit_summary_path=str(audit.summary_path),
        audit=audit,
    )
    task = asyncio.create_task(
        _run_full_live_job(
            job_id=job.job_id,
            request=request,
            resolved=resolved,
            manager=manager,
            audit=audit,
        ),
        name=f"modelcouncil-full-live-{job.job_id}",
    )
    await manager.set_task(job.job_id, task)
    return job


async def _run_full_live_job(
    *,
    job_id: str,
    request: FullLiveSimulationRequest,
    resolved: ResolvedLLMProvider,
    manager: FullLiveJobManager,
    audit,
) -> None:
    try:
        if manager.cancellation_check(job_id)():
            emit_run_cancelled(audit)
            finalize_run_audit(audit, status="cancelled", request=request)
            await manager.mark_cancelled(job_id)
            return

        await manager.update_status(job_id, FullLiveJobStatus.simulating)
        preset, trait_source, product, result = await asyncio.to_thread(
            _run_core_simulation,
            request,
            audit,
        )
        await manager.set_total_conversations(job_id, result.conversation_count)

        if manager.cancellation_check(job_id)():
            emit_run_cancelled(audit)
            finalize_run_audit(audit, status="cancelled", request=request)
            await manager.mark_cancelled(job_id)
            return

        await manager.update_status(job_id, FullLiveJobStatus.rendering)
        settings = get_settings()
        outcome = await render_all_conversations_live(
            entries=result.conversations,
            provider=resolved.provider,
            product_context=ProductLanguageContext.from_product(product),
            concurrency=resolved.concurrency,
            cache_prime_requests=settings.deepseek_cache_prime_requests,
            language_source=resolved.provider_id,
            pricing=resolved.pricing,
            on_progress=lambda progress: manager.update_progress(job_id, progress),
            is_cancelled=manager.cancellation_check(job_id),
            audit=audit,
        )
        result.conversations = outcome.entries

        if outcome.cancelled or manager.cancellation_check(job_id)():
            emit_run_cancelled(audit)
            finalize_run_audit(audit, status="cancelled", request=request)
            await manager.mark_cancelled(job_id)
            return

        response = build_run_response(
            request=request,
            preset=preset,
            trait_source=trait_source,
            product=product,
            result=result,
            dialogue_stats=outcome.stats,
            llm_provider=resolved.provider_id,
            llm_model=resolved.model_id,
        )
        emit_run_completed(audit, response)
        finalize_run_audit(audit, status="completed", request=request, final_result=response)
        await manager.complete(job_id, response)
    except asyncio.CancelledError:
        emit_run_cancelled(audit)
        finalize_run_audit(audit, status="cancelled", request=request)
        await manager.mark_cancelled(job_id)
        raise
    except Exception as exc:
        emit_run_failed(audit, exc)
        finalize_run_audit(
            audit,
            status="failed",
            request=request,
            warnings=(f"{type(exc).__name__}: backend processing failed",),
        )
        await manager.fail(job_id, exc)
