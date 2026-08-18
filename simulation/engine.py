from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from dataclasses import dataclass, field

import networkx as nx

from simulation.analytics.social_dynamics import compute_social_dynamics_metrics
from simulation.behaviour.purchase import derive_purchase_intent
from simulation.conversation.ledger import (
    ConversationLanguageContext,
    ConversationLedgerEntry,
)
from simulation.conversation.router import ConversationContext, ConversationRouter
from simulation.conversation.scheduler import schedule_conversations
from simulation.domain.agent import ConsumerAgent, clamp01
from simulation.network.knn_graph import build_knn_graph
from simulation.opinion.aggregator import TopicEvidence, aggregate_round_evidence
from simulation.opinion.dynamics_config import (
    DEFAULT_INFLUENCE_DYNAMICS,
    InfluenceDynamicsConfig,
)
from simulation.opinion.delta import AgentStateDelta
from simulation.product.baseline_evaluation import evaluate_baseline
from simulation.product.fit import ConsumerProductFit, consumer_product_fit
from simulation.product.knowledge import ProductKnowledge
from simulation.product.semantic_profile import (
    ProductSemanticProfile,
    build_product_semantic_profile,
)
from simulation.audit.logger import RunAuditSink


@dataclass(frozen=True, slots=True)
class SimulationConfig:
    rounds: int = 20
    seed: int = 42
    k: int = 14
    max_conversations_per_agent: int = 2
    initiator_rate: float = 0.20
    weak_tie_rate: float = 0.05
    cooldown_rounds: int = 2
    simulated_minutes_per_round: int = 5
    checkpoint_limit: int = 80

    def __post_init__(self) -> None:
        if self.rounds < 1:
            raise ValueError("rounds must be at least 1")
        if self.k < 1:
            raise ValueError("k must be at least 1")
        if self.max_conversations_per_agent < 1:
            raise ValueError("max conversations must be at least 1")
        if not 0.0 <= self.initiator_rate <= 1.0:
            raise ValueError("initiator_rate must be between 0 and 1")
        if not 0.0 <= self.weak_tie_rate <= 1.0:
            raise ValueError("weak_tie_rate must be between 0 and 1")
        if self.checkpoint_limit < 1:
            raise ValueError("checkpoint_limit must be at least 1")


@dataclass(frozen=True, slots=True)
class TimelinePoint:
    round_index: int
    mean_opinion: float
    mean_purchase_intent: float
    positive_share: float
    neutral_share: float
    negative_share: float
    conversation_count: int


@dataclass(frozen=True, slots=True)
class ReplayAgentState:
    agent_id: int
    overall_opinion: float
    purchase_intent: float
    confidence: float


@dataclass(frozen=True, slots=True)
class RoundCheckpoint:
    round_index: int
    agent_states: tuple[ReplayAgentState, ...]
    active_conversation_ids: tuple[str, ...]


@dataclass(slots=True)
class SimulationResult:
    synthetic: bool
    config: SimulationConfig
    population: list[ConsumerAgent]
    graph: nx.Graph
    timeline: list[TimelinePoint]
    conversations: list[ConversationLedgerEntry] = field(default_factory=list)
    checkpoints: list[RoundCheckpoint] = field(default_factory=list)

    @property
    def conversation_count(self) -> int:
        return len(self.conversations)


class SimulationEngine:
    def __init__(
        self,
        conversation_router: ConversationRouter | None = None,
        influence_dynamics: InfluenceDynamicsConfig | None = None,
    ):
        self.conversation_router = conversation_router or ConversationRouter()
        self.influence_dynamics = influence_dynamics or DEFAULT_INFLUENCE_DYNAMICS

    def run(
        self,
        product: ProductKnowledge,
        population: list[ConsumerAgent],
        config: SimulationConfig,
        *,
        audit: RunAuditSink | None = None,
    ) -> SimulationResult:
        if len(population) < 2:
            raise ValueError("simulation requires at least two consumers")

        agents = deepcopy(population)
        if audit is not None:
            audit.emit(
                "simulation.dynamics_configuration",
                {
                    "version": self.influence_dynamics.version,
                    "max_topic_delta": self.influence_dynamics.max_topic_delta,
                    "saturation_beta": self.influence_dynamics.saturation_beta,
                    "base_noise_std": self.influence_dynamics.base_noise_std,
                    "noise_floor": self.influence_dynamics.noise_floor,
                    "max_noise_to_signal_ratio": self.influence_dynamics.max_noise_to_signal_ratio,
                    "weak_tie_exploration_weight": self.influence_dynamics.weak_tie_exploration_weight,
                    "disagreement_information_weight": self.influence_dynamics.disagreement_information_weight,
                },
            )
        product_profile = build_product_semantic_profile(product, audit=audit)
        product_fits = {
            agent.agent_id: consumer_product_fit(
                agent,
                product,
                product_profile,
                seed=config.seed,
                audit=audit,
            )
            for agent in agents
        }
        self._initialize_baseline(
            agents,
            product,
            product_profile,
            product_fits,
            config.seed,
            audit=audit,
        )
        initial_opinions = {
            agent.agent_id: agent.state.overall_opinion
            for agent in agents
        }
        graph = build_knn_graph(
            agents,
            k=config.k,
            weak_tie_rate=config.weak_tie_rate,
            seed=config.seed,
            audit=audit,
        )

        timeline = [self._timeline_point(0, agents, 0)]
        conversation_ledger: list[ConversationLedgerEntry] = []
        replay_ids = tuple(
            agent.agent_id for agent in agents[: min(config.checkpoint_limit, len(agents))]
        )
        checkpoints = [self._checkpoint(0, agents, replay_ids, ())]
        recent_topics_by_agent: dict[int, tuple[str, ...]] = {}
        recent_topics_by_edge: dict[tuple[int, int], tuple[str, ...]] = {}
        price_contexts = {
            agent_id: fit.price_context
            for agent_id, fit in product_fits.items()
            if fit.price_context is not None
        }

        for round_index in range(1, config.rounds + 1):
            snapshot = deepcopy(agents)
            if audit is not None:
                audit.emit(
                    "round.started",
                    {
                        "population_size": len(snapshot),
                        "mean_opinion": sum(agent.state.overall_opinion for agent in snapshot) / len(snapshot),
                        "mean_purchase_intent": sum(agent.state.purchase_intent for agent in snapshot) / len(snapshot),
                    },
                    round_index=round_index,
                )
            pairs = schedule_conversations(
                agents=snapshot,
                graph=graph,
                round_index=round_index,
                max_conversations_per_agent=config.max_conversations_per_agent,
                cooldown_rounds=config.cooldown_rounds,
                seed=config.seed,
                initiator_rate=config.initiator_rate,
                dynamics=self.influence_dynamics,
                audit=audit,
            )

            evidence_by_listener: dict[int, list[TopicEvidence]] = defaultdict(list)
            interaction_counts: dict[int, int] = defaultdict(int)
            context = ConversationContext(
                snapshot=_by_id(snapshot),
                graph=graph,
                seed=config.seed,
                price_contexts=price_contexts,
                recent_topics_by_agent=dict(recent_topics_by_agent),
                recent_topics_by_edge=dict(recent_topics_by_edge),
                audit=audit,
            )
            round_topic_records: list[tuple[int, int, str]] = []

            for pair in pairs:
                result = self.conversation_router.generate(pair, context)
                edge = graph.edges[pair.agent_a_id, pair.agent_b_id]
                conversation_ledger.append(
                    ConversationLedgerEntry(
                        round_index=round_index,
                        pair=pair,
                        result=result,
                        language_context=ConversationLanguageContext.from_agents(
                            context.snapshot[pair.agent_a_id],
                            context.snapshot[pair.agent_b_id],
                            agent_a_price_context=product_fits[pair.agent_a_id].price_context,
                            agent_b_price_context=product_fits[pair.agent_b_id].price_context,
                        ),
                        trust=float(edge.get("trust", 0.4)),
                        relationship_strength=float(
                            edge.get("relationship_strength", 0.4)
                        ),
                        similarity=float(edge.get("similarity", 0.3)),
                        weak_tie=bool(edge.get("weak_tie", False)),
                    )
                )
                interaction_counts[pair.agent_a_id] += 1
                interaction_counts[pair.agent_b_id] += 1
                self._record_graph_interaction(graph, pair.agent_a_id, pair.agent_b_id, round_index)

                for message in result.messages:
                    speaker = context.snapshot[message.speaker_id]
                    for topic, stance in message.topic_effects.items():
                        round_topic_records.append(
                            (message.speaker_id, message.listener_id, topic)
                        )
                        topic_evidence = TopicEvidence(
                            topic=topic,
                            stance=stance,
                            argument_strength=message.argument_strength,
                            trust=float(edge.get("trust", 0.4)),
                            relationship_strength=float(
                                edge.get("relationship_strength", 0.4)
                            ),
                            similarity=float(edge.get("similarity", 0.3)),
                            speaker_confidence=message.confidence,
                            speaker_knowledge=speaker.state.knowledge,
                            novelty=1.0,
                        )
                        evidence_by_listener[message.listener_id].append(topic_evidence)
                        if audit is not None:
                            audit.emit(
                                "evidence.created",
                                {
                                    "speaker_id": message.speaker_id,
                                    "listener_id": message.listener_id,
                                    "evidence": topic_evidence,
                                },
                                round_index=round_index,
                                conversation_id=pair.conversation_id,
                                agent_ids=[message.speaker_id, message.listener_id],
                            )

            self._commit_topic_history(
                recent_topics_by_agent,
                recent_topics_by_edge,
                round_topic_records,
            )
            deltas = self._calculate_deltas(
                snapshot=snapshot,
                evidence_by_listener=evidence_by_listener,
                interaction_counts=interaction_counts,
                round_index=round_index,
                seed=config.seed,
                dynamics=self.influence_dynamics,
                audit=audit,
            )
            agents = self._commit_deltas(
                snapshot,
                deltas,
                product_fits,
                round_index=round_index,
                audit=audit,
            )
            round_point = self._timeline_point(round_index, agents, len(pairs))
            timeline.append(round_point)
            checkpoints.append(
                self._checkpoint(
                    round_index,
                    agents,
                    replay_ids,
                    tuple(pair.conversation_id for pair in pairs),
                )
            )
            if audit is not None:
                audit.emit(
                    "round.completed",
                    {
                        "conversation_count": len(pairs),
                        "timeline": round_point,
                        "recent_topic_agents": len(recent_topics_by_agent),
                        "recent_topic_edges": len(recent_topics_by_edge),
                    },
                    round_index=round_index,
                )

        if audit is not None:
            social_metrics = compute_social_dynamics_metrics(
                initial_opinions,
                agents,
                conversation_ledger,
            )
            audit.emit(
                "social_dynamics.summary",
                {
                    "mean_absolute_opinion_movement": social_metrics.mean_absolute_opinion_movement,
                    "median_absolute_opinion_movement": social_metrics.median_absolute_opinion_movement,
                    "upward_movers": social_metrics.upward_movers,
                    "downward_movers": social_metrics.downward_movers,
                    "unchanged_agents": social_metrics.unchanged_agents,
                    "initial_opinion_std": social_metrics.initial_opinion_std,
                    "final_opinion_std": social_metrics.final_opinion_std,
                    "mean_contact_opinion_gap": social_metrics.mean_contact_opinion_gap,
                    "selected_weak_tie_share": social_metrics.selected_weak_tie_share,
                },
            )

        return SimulationResult(
            synthetic=True,
            config=config,
            population=agents,
            graph=graph,
            timeline=timeline,
            conversations=conversation_ledger,
            checkpoints=checkpoints,
        )

    @staticmethod
    def _initialize_baseline(
        agents: list[ConsumerAgent],
        product: ProductKnowledge,
        product_profile: ProductSemanticProfile,
        product_fits: dict[int, ConsumerProductFit],
        seed: int,
        *,
        audit: RunAuditSink | None = None,
    ) -> None:
        for agent in agents:
            agent.state.beliefs = evaluate_baseline(
                agent,
                product,
                seed,
                profile=product_profile,
                fit=product_fits[agent.agent_id],
                audit=audit,
            )
            agent.state.knowledge = clamp01(0.12 + 0.10 * agent.traits.logicality)
            agent.state.product_salience = max(agent.state.product_salience, 0.60)
            derive_purchase_intent(
                agent,
                fit=product_fits[agent.agent_id],
                audit=audit,
                round_index=0,
                phase="baseline",
            )
            agent.state.normalize()
            if audit is not None:
                audit.emit(
                    "baseline.state_initialized",
                    {
                        "agent_id": agent.agent_id,
                        "state": agent.state,
                        "consumer_fit": product_fits[agent.agent_id],
                    },
                    round_index=0,
                    agent_ids=[agent.agent_id],
                )

    @staticmethod
    def _calculate_deltas(
        snapshot: list[ConsumerAgent],
        evidence_by_listener: dict[int, list[TopicEvidence]],
        interaction_counts: dict[int, int],
        round_index: int,
        seed: int,
        dynamics: InfluenceDynamicsConfig,
        audit: RunAuditSink | None = None,
    ) -> dict[int, AgentStateDelta]:
        deltas: dict[int, AgentStateDelta] = {}
        for agent in snapshot:
            evidence = evidence_by_listener.get(agent.agent_id, [])
            aggregation = aggregate_round_evidence(
                agent,
                evidence,
                max_topic_delta=dynamics.max_topic_delta,
                saturation_beta=dynamics.saturation_beta,
                noise_std=dynamics.base_noise_std,
                noise_floor=dynamics.noise_floor,
                max_noise_to_signal_ratio=dynamics.max_noise_to_signal_ratio,
                seed=seed + round_index * 1009,
                audit=audit,
                round_index=round_index,
            )
            conversations = interaction_counts.get(agent.agent_id, 0)
            delta = AgentStateDelta(
                belief_updates=aggregation.belief_updates,
                confidence_delta=aggregation.confidence_delta,
                knowledge_delta=min(0.04, conversations * 0.012),
                salience_delta=(-0.012 + min(0.04, conversations * 0.018)),
            )
            deltas[agent.agent_id] = delta
            if audit is not None:
                audit.emit(
                    "state.delta",
                    {
                        "agent_id": agent.agent_id,
                        "interaction_count": conversations,
                        "delta": delta,
                    },
                    round_index=round_index,
                    agent_ids=[agent.agent_id],
                )
        return deltas

    @staticmethod
    def _commit_deltas(
        snapshot: list[ConsumerAgent],
        deltas: dict[int, AgentStateDelta],
        product_fits: dict[int, ConsumerProductFit],
        *,
        round_index: int,
        audit: RunAuditSink | None = None,
    ) -> list[ConsumerAgent]:
        committed = deepcopy(snapshot)
        before_by_id = _by_id(snapshot)
        for agent in committed:
            delta = deltas[agent.agent_id]
            before_state = deepcopy(before_by_id[agent.agent_id].state)
            agent.state.beliefs.apply(delta.belief_updates)
            agent.state.confidence = clamp01(agent.state.confidence + delta.confidence_delta)
            agent.state.knowledge = clamp01(agent.state.knowledge + delta.knowledge_delta)
            agent.state.product_salience = clamp01(
                agent.state.product_salience + delta.salience_delta
            )
            derive_purchase_intent(
                agent,
                fit=product_fits[agent.agent_id],
                audit=audit,
                round_index=round_index,
                phase="round_commit",
            )
            agent.state.normalize()
            if audit is not None:
                audit.emit(
                    "state.committed",
                    {
                        "agent_id": agent.agent_id,
                        "before": before_state,
                        "after": agent.state,
                    },
                    round_index=round_index,
                    agent_ids=[agent.agent_id],
                )
        return committed

    @staticmethod
    def _commit_topic_history(
        recent_topics_by_agent: dict[int, tuple[str, ...]],
        recent_topics_by_edge: dict[tuple[int, int], tuple[str, ...]],
        records: list[tuple[int, int, str]],
        *,
        limit: int = 4,
    ) -> None:
        for speaker_id, listener_id, topic in records:
            for agent_id in (speaker_id, listener_id):
                history = recent_topics_by_agent.get(agent_id, ()) + (topic,)
                recent_topics_by_agent[agent_id] = history[-limit:]
            edge_key = tuple(sorted((speaker_id, listener_id)))
            edge_history = recent_topics_by_edge.get(edge_key, ()) + (topic,)
            recent_topics_by_edge[edge_key] = edge_history[-limit:]

    @staticmethod
    def _record_graph_interaction(
        graph: nx.Graph,
        agent_a_id: int,
        agent_b_id: int,
        round_index: int,
    ) -> None:
        edge = graph.edges[agent_a_id, agent_b_id]
        edge["last_interaction_round"] = round_index
        edge["interaction_count"] = int(edge.get("interaction_count", 0)) + 1

    @staticmethod
    def _checkpoint(
        round_index: int,
        agents: list[ConsumerAgent],
        replay_ids: tuple[int, ...],
        active_conversation_ids: tuple[str, ...],
    ) -> RoundCheckpoint:
        by_id = _by_id(agents)
        return RoundCheckpoint(
            round_index=round_index,
            agent_states=tuple(
                ReplayAgentState(
                    agent_id=agent_id,
                    overall_opinion=by_id[agent_id].state.overall_opinion,
                    purchase_intent=by_id[agent_id].state.purchase_intent,
                    confidence=by_id[agent_id].state.confidence,
                )
                for agent_id in replay_ids
            ),
            active_conversation_ids=active_conversation_ids,
        )

    @staticmethod
    def _timeline_point(
        round_index: int,
        agents: list[ConsumerAgent],
        conversation_count: int,
    ) -> TimelinePoint:
        size = len(agents)
        opinions = [agent.state.overall_opinion for agent in agents]
        purchases = [agent.state.purchase_intent for agent in agents]
        positive = sum(value > 0.20 for value in opinions) / size
        negative = sum(value < -0.20 for value in opinions) / size
        neutral = 1.0 - positive - negative
        return TimelinePoint(
            round_index=round_index,
            mean_opinion=sum(opinions) / size,
            mean_purchase_intent=sum(purchases) / size,
            positive_share=positive,
            neutral_share=neutral,
            negative_share=negative,
            conversation_count=conversation_count,
        )


def _by_id(agents: list[ConsumerAgent]) -> dict[int, ConsumerAgent]:
    return {agent.agent_id: agent for agent in agents}
