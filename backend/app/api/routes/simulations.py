from fastapi import APIRouter, HTTPException, status

from backend.app.schemas.simulation import (
    DialogueMode,
    FullLiveSimulationRequest,
    FullLiveStartResponse,
    FullLiveStatusView,
    SimulationPreviewRequest,
    SimulationPreviewResponse,
    SimulationRunResponse,
)
from backend.app.services.full_live_jobs import (
    FullLiveJobRecord,
    FullLiveJobStatus,
    full_live_job_manager,
)
from backend.app.services.full_live_service import (
    FullLiveConfigurationError,
    start_full_live_job,
)
from backend.app.services.simulation_service import build_simulation_preview, run_simulation

router = APIRouter(prefix="/simulations", tags=["simulations"])


def _progress_ratio(job: FullLiveJobRecord) -> float:
    if job.status is FullLiveJobStatus.completed:
        return 1.0
    if job.total_conversations is not None:
        if job.total_conversations == 0:
            return 0.0
        return min(1.0, job.processed_conversations / job.total_conversations)
    if job.status in {FullLiveJobStatus.simulating, FullLiveJobStatus.cancelling}:
        return 0.05
    return 0.0


def _full_live_status_view(job: FullLiveJobRecord) -> FullLiveStatusView:
    return FullLiveStatusView(
        job_id=job.job_id,
        status=job.status.value,
        product_name=job.product_name,
        population_mode=job.population_mode,
        rounds=job.rounds,
        seed=job.seed,
        estimated_upper_bound_conversations=job.estimated_upper_bound_conversations,
        llm_provider=job.llm_provider,
        llm_model=job.llm_model,
        total_conversations=job.total_conversations,
        processed_conversations=job.processed_conversations,
        successful_renders=job.successful_renders,
        fallback_count=job.fallback_count,
        progress_ratio=_progress_ratio(job),
        prompt_tokens=job.prompt_tokens,
        prompt_cache_hit_tokens=job.prompt_cache_hit_tokens,
        prompt_cache_miss_tokens=job.prompt_cache_miss_tokens,
        completion_tokens=job.completion_tokens,
        total_tokens=job.total_tokens,
        cache_hit_ratio=job.cache_hit_ratio,
        average_latency_ms=job.average_latency_ms,
        max_latency_ms=job.max_latency_ms,
        estimated_cost_usd=job.estimated_cost_usd,
        provider_model=job.provider_model,
        error_message=job.error_message,
        cancel_requested=job.cancel_requested,
    )


@router.post("/preview", response_model=SimulationPreviewResponse)
def preview_simulation(request: SimulationPreviewRequest) -> SimulationPreviewResponse:
    return build_simulation_preview(request)


@router.post(
    "/full-live",
    response_model=FullLiveStartResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def start_full_live_simulation(
    request: FullLiveSimulationRequest,
) -> FullLiveStartResponse:
    try:
        job = await start_full_live_job(request)
    except FullLiveConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    return FullLiveStartResponse(
        job_id=job.job_id,
        status=FullLiveJobStatus.queued.value,
        estimated_upper_bound_conversations=job.estimated_upper_bound_conversations,
        llm_provider=job.llm_provider,
        llm_model=job.llm_model,
    )


@router.get("/full-live/{job_id}", response_model=FullLiveStatusView)
async def get_full_live_simulation_status(job_id: str) -> FullLiveStatusView:
    job = await full_live_job_manager.get(job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Full Live job not found.")
    return _full_live_status_view(job)


@router.get("/full-live/{job_id}/result", response_model=SimulationRunResponse)
async def get_full_live_simulation_result(job_id: str) -> SimulationRunResponse:
    job = await full_live_job_manager.get(job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Full Live job not found.")
    if job.status is FullLiveJobStatus.cancelled:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Full Live job was cancelled.")
    if job.status is FullLiveJobStatus.failed:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=job.error_message or "Full Live job failed.",
        )
    if job.status is not FullLiveJobStatus.completed or job.result is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Full Live result is not ready yet.",
        )
    return job.result


@router.post("/full-live/{job_id}/cancel", response_model=FullLiveStatusView)
async def cancel_full_live_simulation(job_id: str) -> FullLiveStatusView:
    job = await full_live_job_manager.request_cancel(job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Full Live job not found.")
    return _full_live_status_view(job)


@router.post("/run", response_model=SimulationRunResponse)
async def execute_simulation(request: SimulationPreviewRequest) -> SimulationRunResponse:
    if request.dialogue_mode is DialogueMode.full_live:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Full Live must use the asynchronous /simulations/full-live job endpoint.",
        )
    return await run_simulation(request)
