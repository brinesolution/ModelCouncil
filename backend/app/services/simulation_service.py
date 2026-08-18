from __future__ import annotations

import asyncio
from pathlib import Path

from backend.app.core.config import get_settings, resolve_deepseek_api_key
from backend.app.schemas.simulation import (
    ConversationView,
    DashboardAnalyticsView,
    DialogueStatsView,
    NetworkEdgeView,
    NetworkNodeView,
    NetworkView,
    PurchaseIntentDistributionView,
    ReplayAgentStateView,
    ReplayCheckpointView,
    ReplayConversationEdgeView,
    SimulationPreviewRequest,
    SimulationPreviewResponse,
    SimulationPresetView,
    SimulationRunResponse,
    SimulationSummaryView,
    TimelinePointView,
    TopicPressurePointView,
)
from simulation.analytics.dashboard import build_dashboard_analytics
from simulation.config.presets import PopulationPreset
from simulation.conversation.ledger import ProductLanguageContext
from simulation.conversation.replay_selector import select_replay_conversations
from simulation.conversation.render_pipeline import (
    DialoguePricing,
    DialogueRenderStats,
    render_conversation_ledger,
)
from simulation.engine import SimulationConfig, SimulationEngine, SimulationResult
from simulation.llm.deepseek import DeepSeekProvider
from simulation.population.excel_repository import ExcelTraitRepository
from simulation.population.generator import generate_population
from simulation.product.knowledge import ProductKnowledge
from simulation.audit.logger import RunAuditSink
from backend.app.services.run_audit_service import (
    create_run_audit,
    emit_run_completed,
    emit_run_failed,
    finalize_run_audit,
)
from backend.app.services.simulation_config_service import resolve_effective_preset

PROJECT_ROOT = Path(__file__).resolve().parents[3]
TRAIT_ROOT = PROJECT_ROOT / "data" / "traits"


def _preset_view(preset: PopulationPreset) -> SimulationPresetView:
    return SimulationPresetView(
        population_size=preset.population_size,
        base_k=preset.base_k,
        max_conversations_per_round=preset.max_conversations_per_round,
        initiator_rate=preset.initiator_rate,
        weak_tie_rate=preset.weak_tie_rate,
        simulated_minutes_per_round=preset.simulated_minutes_per_round,
    )


def build_simulation_preview(
    request: SimulationPreviewRequest,
) -> SimulationPreviewResponse:
    preset = resolve_effective_preset(request)
    product = _product_knowledge(request)

    return SimulationPreviewResponse(
        status="initialized",
        product_name=request.product.name,
        billing_cadence=product.resolved_billing_cadence,
        advanced_config_enabled=request.advanced_config is not None,
        preset=_preset_view(preset),
        rounds=request.rounds,
        dialogue_mode=request.dialogue_mode,
        seed=request.seed,
        note=(
            "Preview uses the same population and conversation preset that the full "
            "simulation endpoint will execute. Outputs are synthetic."
        ),
    )


async def run_simulation(request: SimulationPreviewRequest) -> SimulationRunResponse:
    audit = create_run_audit(request, run_kind="normal")
    try:
        preset, trait_source, product, result = await asyncio.to_thread(
            _run_core_simulation,
            request,
            audit,
        )

        provider = _deepseek_provider_or_none()
        settings = get_settings()
        rendered_entries, dialogue_stats = await render_conversation_ledger(
            entries=result.conversations,
            dialogue_mode=request.dialogue_mode.value,
            provider=provider,
            concurrency=settings.deepseek_render_concurrency,
            product_context=ProductLanguageContext.from_product(product),
            max_live_requests=settings.deepseek_max_live_requests_per_run,
            cache_prime_requests=settings.deepseek_cache_prime_requests,
            pricing=DialoguePricing(
                cache_hit_usd_per_million=settings.deepseek_cache_hit_usd_per_million,
                cache_miss_usd_per_million=settings.deepseek_cache_miss_usd_per_million,
                output_usd_per_million=settings.deepseek_output_usd_per_million,
            ),
            audit=audit,
        )
        result.conversations = rendered_entries

        response = build_run_response(
            request=request,
            preset=preset,
            trait_source=trait_source,
            product=product,
            result=result,
            dialogue_stats=dialogue_stats,
        )
        emit_run_completed(audit, response)
        finalize_run_audit(audit, status="completed", request=request, final_result=response)
        return response
    except Exception as exc:
        emit_run_failed(audit, exc)
        finalize_run_audit(
            audit,
            status="failed",
            request=request,
            warnings=(f"{type(exc).__name__}: backend processing failed",),
        )
        raise


def build_run_response(
    *,
    request: SimulationPreviewRequest,
    preset: PopulationPreset,
    trait_source: str,
    product: ProductKnowledge,
    result: SimulationResult,
    dialogue_stats: DialogueRenderStats,
    llm_provider: str | None = None,
    llm_model: str | None = None,
) -> SimulationRunResponse:
    final = result.timeline[-1]
    return SimulationRunResponse(
        synthetic=True,
        status="completed",
        product_name=product.name,
        billing_cadence=product.resolved_billing_cadence,
        population_mode=request.population_mode,
        advanced_config_enabled=request.advanced_config is not None,
        dialogue_mode=request.dialogue_mode,
        llm_provider=llm_provider,
        llm_model=llm_model,
        rounds=request.rounds,
        seed=request.seed,
        preset=_preset_view(preset),
        summary=SimulationSummaryView(
            population_size=len(result.population),
            conversation_count=result.conversation_count,
            final_mean_opinion=final.mean_opinion,
            final_mean_purchase_intent=final.mean_purchase_intent,
            base_k=preset.base_k,
        ),
        timeline=[
            TimelinePointView(
                round=point.round_index,
                mean_opinion=point.mean_opinion,
                mean_purchase_intent=point.mean_purchase_intent,
                positive_share=point.positive_share,
                neutral_share=point.neutral_share,
                negative_share=point.negative_share,
                conversation_count=point.conversation_count,
            )
            for point in result.timeline
        ],
        network=_network_view(result.population, result.graph),
        selected_conversations=_conversation_views(result.conversations),
        dialogue_stats=_dialogue_stats_view(dialogue_stats),
        analytics=_dashboard_analytics_view(result),
        replay=_replay_views(result, preset.simulated_minutes_per_round),
        trait_source=trait_source,
    )


def _run_core_simulation(
    request: SimulationPreviewRequest,
    audit: RunAuditSink | None = None,
) -> tuple[PopulationPreset, str, ProductKnowledge, SimulationResult]:
    preset = resolve_effective_preset(request)
    trait_repository, trait_source = _trait_repository()
    population = generate_population(
        size=preset.population_size,
        seed=request.seed,
        traits=trait_repository,
        audit=audit,
    )
    product = _product_knowledge(request)
    result = SimulationEngine().run(
        product=product,
        population=population,
        config=SimulationConfig(
            rounds=request.rounds,
            seed=request.seed,
            k=preset.base_k,
            max_conversations_per_agent=preset.max_conversations_per_round,
            initiator_rate=preset.initiator_rate,
            weak_tie_rate=preset.weak_tie_rate,
            simulated_minutes_per_round=preset.simulated_minutes_per_round,
            checkpoint_limit=80,
        ),
        audit=audit,
    )
    return preset, trait_source, product, result


def _product_knowledge(request: SimulationPreviewRequest) -> ProductKnowledge:
    return ProductKnowledge(
        name=request.product.name,
        pitch=request.product.pitch,
        category=request.product.category,
        price=request.product.price,
        currency=request.product.currency,
        billing_cadence=request.product.billing_cadence,
    )


def _deepseek_provider_or_none() -> DeepSeekProvider | None:
    settings = get_settings()
    api_key = resolve_deepseek_api_key(settings)
    if not settings.deepseek_live_enabled or not api_key:
        return None
    return DeepSeekProvider(
        api_key=api_key,
        base_url=settings.deepseek_base_url,
        model=settings.deepseek_model,
        thinking=settings.deepseek_thinking,
    )


def _trait_repository() -> tuple[ExcelTraitRepository | None, str]:
    workbooks = (
        [
            path
            for path in TRAIT_ROOT.glob("*.xlsx")
            if not path.name.startswith("~$")
        ]
        if TRAIT_ROOT.exists()
        else []
    )
    if not workbooks:
        return None, "bootstrap"
    return ExcelTraitRepository(TRAIT_ROOT), "excel"


def _network_view(population, graph, limit: int = 80) -> NetworkView:
    sampled = population[:limit]
    sampled_ids = {agent.agent_id for agent in sampled}
    nodes = [
        NetworkNodeView(
            id=agent.agent_id,
            opinion=agent.state.overall_opinion,
            purchase_intent=agent.state.purchase_intent,
            influence=agent.traits.influence_power,
            segment=agent.occupation,
        )
        for agent in sampled
    ]
    edges = [
        NetworkEdgeView(
            source=int(source),
            target=int(target),
            similarity=float(data.get("similarity", 0.0)),
            weak_tie=bool(data.get("weak_tie", False)),
        )
        for source, target, data in graph.edges(data=True)
        if source in sampled_ids and target in sampled_ids
    ][:240]
    return NetworkView(nodes=nodes, edges=edges)


def _conversation_views(entries, limit: int = 12) -> list[ConversationView]:
    selected = select_replay_conversations(entries, limit=limit)
    views: list[ConversationView] = []
    for entry in selected:
        topics = sorted(
            {
                topic
                for message in entry.result.messages
                for topic in message.topic_effects
            }
        )
        views.append(
            ConversationView(
                round=entry.round_index,
                conversation_id=entry.conversation_id,
                agent_a_id=entry.agent_a_id,
                agent_b_id=entry.agent_b_id,
                topics=topics,
                transcript=entry.result.transcript,
                language_source=entry.result.language_source,
                importance=entry.importance,
                llm_selected=entry.llm_selected,
            )
        )
    return views


def _dialogue_stats_view(stats: DialogueRenderStats) -> DialogueStatsView:
    return DialogueStatsView(
        total_conversations=stats.total_conversations,
        selected_for_llm=stats.selected_for_llm,
        llm_rendered=stats.llm_rendered,
        fallback_count=stats.fallback_count,
        background_count=stats.background_count,
        provider_available=stats.provider_available,
        provider_model=stats.provider_model,
        prompt_tokens=stats.prompt_tokens,
        prompt_cache_hit_tokens=stats.prompt_cache_hit_tokens,
        prompt_cache_miss_tokens=stats.prompt_cache_miss_tokens,
        completion_tokens=stats.completion_tokens,
        total_tokens=stats.total_tokens,
        cache_hit_ratio=stats.cache_hit_ratio,
        average_latency_ms=stats.average_latency_ms,
        max_latency_ms=stats.max_latency_ms,
        estimated_cost_usd=stats.estimated_cost_usd,
    )


def _dashboard_analytics_view(result: SimulationResult) -> DashboardAnalyticsView:
    analytics = build_dashboard_analytics(result)
    distribution = analytics.purchase_intent_distribution
    return DashboardAnalyticsView(
        purchase_intent_distribution=PurchaseIntentDistributionView(
            low=distribution.low,
            medium=distribution.medium,
            high=distribution.high,
        ),
        topic_pressure=[
            TopicPressurePointView(
                topic=point.topic,
                raw_score=point.raw_score,
                normalized_score=point.normalized_score,
                support_score=point.support_score,
                criticism_score=point.criticism_score,
                net_score=point.net_score,
                normalized_support=point.normalized_support,
                normalized_criticism=point.normalized_criticism,
            )
            for point in analytics.topic_pressure
        ],
    )


def _replay_views(
    result: SimulationResult,
    simulated_minutes_per_round: int,
) -> list[ReplayCheckpointView]:
    entry_by_id = {entry.conversation_id: entry for entry in result.conversations}
    views: list[ReplayCheckpointView] = []

    for checkpoint in result.checkpoints:
        sampled_ids = {state.agent_id for state in checkpoint.agent_states}
        active_edges: list[ReplayConversationEdgeView] = []
        for conversation_id in checkpoint.active_conversation_ids:
            entry = entry_by_id.get(conversation_id)
            if entry is None:
                continue
            if entry.agent_a_id not in sampled_ids or entry.agent_b_id not in sampled_ids:
                continue
            active_edges.append(
                ReplayConversationEdgeView(
                    conversation_id=conversation_id,
                    source=entry.agent_a_id,
                    target=entry.agent_b_id,
                )
            )

        views.append(
            ReplayCheckpointView(
                round=checkpoint.round_index,
                simulated_minutes=checkpoint.round_index
                * simulated_minutes_per_round,
                nodes=[
                    ReplayAgentStateView(
                        id=state.agent_id,
                        opinion=state.overall_opinion,
                        purchase_intent=state.purchase_intent,
                        confidence=state.confidence,
                    )
                    for state in checkpoint.agent_states
                ],
                active_conversations=active_edges,
            )
        )

    return views
