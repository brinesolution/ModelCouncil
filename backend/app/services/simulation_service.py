from __future__ import annotations

from pathlib import Path

from backend.app.schemas.simulation import (
    ConversationView,
    NetworkEdgeView,
    NetworkNodeView,
    NetworkView,
    SimulationPreviewRequest,
    SimulationPreviewResponse,
    SimulationPresetView,
    SimulationRunResponse,
    SimulationSummaryView,
    TimelinePointView,
)
from simulation.config.presets import PopulationPreset, get_population_preset
from simulation.engine import SimulationConfig, SimulationEngine
from simulation.population.excel_repository import ExcelTraitRepository
from simulation.population.generator import generate_population
from simulation.product.knowledge import ProductKnowledge

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
    preset = get_population_preset(request.population_mode.value)

    return SimulationPreviewResponse(
        status="initialized",
        product_name=request.product.name,
        preset=_preset_view(preset),
        rounds=request.rounds,
        dialogue_mode=request.dialogue_mode,
        seed=request.seed,
        note=(
            "Preview uses the same population and conversation preset that the full "
            "simulation endpoint will execute. Outputs are synthetic." 
        ),
    )


def run_simulation(request: SimulationPreviewRequest) -> SimulationRunResponse:
    preset = get_population_preset(request.population_mode.value)
    trait_repository, trait_source = _trait_repository()
    population = generate_population(
        size=preset.population_size,
        seed=request.seed,
        traits=trait_repository,
    )
    product = ProductKnowledge(
        name=request.product.name,
        pitch=request.product.pitch,
        category=request.product.category,
        price=request.product.price,
        currency=request.product.currency,
    )
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
        ),
    )

    final = result.timeline[-1]
    return SimulationRunResponse(
        synthetic=True,
        status="completed",
        product_name=product.name,
        population_mode=request.population_mode,
        dialogue_mode=request.dialogue_mode,
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
        trait_source=trait_source,
    )


def _trait_repository() -> tuple[ExcelTraitRepository | None, str]:
    workbooks = list(TRAIT_ROOT.glob("*.xlsx")) if TRAIT_ROOT.exists() else []
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
    views: list[ConversationView] = []
    for entry in entries[:limit]:
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
            )
        )
    return views
