from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from dataclasses import dataclass, field

import networkx as nx

from simulation.behaviour.purchase import derive_purchase_intent
from simulation.conversation.models import ConversationResult
from simulation.conversation.router import ConversationContext, ConversationRouter
from simulation.conversation.scheduler import schedule_conversations
from simulation.domain.agent import ConsumerAgent, clamp01
from simulation.network.knn_graph import build_knn_graph
from simulation.opinion.aggregator import TopicEvidence, aggregate_round_evidence
from simulation.opinion.delta import AgentStateDelta
from simulation.product.baseline_evaluation import evaluate_baseline
from simulation.product.knowledge import ProductKnowledge


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
class ConversationLedgerEntry:
    round_index: int
    conversation_id: str
    agent_a_id: int
    agent_b_id: int
    result: ConversationResult


@dataclass(slots=True)
class SimulationResult:
    synthetic: bool
    config: SimulationConfig
    population: list[ConsumerAgent]
    graph: nx.Graph
    timeline: list[TimelinePoint]
    conversations: list[ConversationLedgerEntry] = field(default_factory=list)

    @property
    def conversation_count(self) -> int:
        return len(self.conversations)


class SimulationEngine:
    def __init__(self, conversation_router: ConversationRouter | None = None):
        self.conversation_router = conversation_router or ConversationRouter()

    def run(
        self,
        product: ProductKnowledge,
        population: list[ConsumerAgent],
        config: SimulationConfig,
    ) -> SimulationResult:
        if len(population) < 2:
            raise ValueError("simulation requires at least two consumers")

        agents = deepcopy(population)
        self._initialize_baseline(agents, product, config.seed)
        graph = build_knn_graph(
            agents,
            k=config.k,
            weak_tie_rate=config.weak_tie_rate,
            seed=config.seed,
        )

        timeline = [self._timeline_point(0, agents, 0)]
        conversation_ledger: list[ConversationLedgerEntry] = []

        for round_index in range(1, config.rounds + 1):
            snapshot = deepcopy(agents)
            pairs = schedule_conversations(
                agents=snapshot,
                graph=graph,
                round_index=round_index,
                max_conversations_per_agent=config.max_conversations_per_agent,
                cooldown_rounds=config.cooldown_rounds,
                seed=config.seed,
                initiator_rate=config.initiator_rate,
            )

            evidence_by_listener: dict[int, list[TopicEvidence]] = defaultdict(list)
            interaction_counts: dict[int, int] = defaultdict(int)
            context = ConversationContext(snapshot=_by_id(snapshot), graph=graph, seed=config.seed)

            for pair in pairs:
                result = self.conversation_router.generate(pair, context)
                conversation_ledger.append(
                    ConversationLedgerEntry(
                        round_index=round_index,
                        conversation_id=pair.conversation_id,
                        agent_a_id=pair.agent_a_id,
                        agent_b_id=pair.agent_b_id,
                        result=result,
                    )
                )
                interaction_counts[pair.agent_a_id] += 1
                interaction_counts[pair.agent_b_id] += 1
                self._record_graph_interaction(graph, pair.agent_a_id, pair.agent_b_id, round_index)

                edge = graph.edges[pair.agent_a_id, pair.agent_b_id]
                for message in result.messages:
                    speaker = context.snapshot[message.speaker_id]
                    for topic, stance in message.topic_effects.items():
                        evidence_by_listener[message.listener_id].append(
                            TopicEvidence(
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
                        )

            deltas = self._calculate_deltas(
                snapshot=snapshot,
                evidence_by_listener=evidence_by_listener,
                interaction_counts=interaction_counts,
                round_index=round_index,
                seed=config.seed,
            )
            agents = self._commit_deltas(snapshot, deltas)
            timeline.append(self._timeline_point(round_index, agents, len(pairs)))

        return SimulationResult(
            synthetic=True,
            config=config,
            population=agents,
            graph=graph,
            timeline=timeline,
            conversations=conversation_ledger,
        )

    @staticmethod
    def _initialize_baseline(
        agents: list[ConsumerAgent],
        product: ProductKnowledge,
        seed: int,
    ) -> None:
        for agent in agents:
            agent.state.beliefs = evaluate_baseline(agent, product, seed)
            agent.state.knowledge = clamp01(0.12 + 0.10 * agent.traits.logicality)
            agent.state.product_salience = max(agent.state.product_salience, 0.60)
            derive_purchase_intent(agent)
            agent.state.normalize()

    @staticmethod
    def _calculate_deltas(
        snapshot: list[ConsumerAgent],
        evidence_by_listener: dict[int, list[TopicEvidence]],
        interaction_counts: dict[int, int],
        round_index: int,
        seed: int,
    ) -> dict[int, AgentStateDelta]:
        deltas: dict[int, AgentStateDelta] = {}
        for agent in snapshot:
            evidence = evidence_by_listener.get(agent.agent_id, [])
            aggregation = aggregate_round_evidence(
                agent,
                evidence,
                seed=seed + round_index * 1009,
            )
            conversations = interaction_counts.get(agent.agent_id, 0)
            deltas[agent.agent_id] = AgentStateDelta(
                belief_updates=aggregation.belief_updates,
                confidence_delta=aggregation.confidence_delta,
                knowledge_delta=min(0.04, conversations * 0.012),
                salience_delta=(-0.012 + min(0.04, conversations * 0.018)),
            )
        return deltas

    @staticmethod
    def _commit_deltas(
        snapshot: list[ConsumerAgent],
        deltas: dict[int, AgentStateDelta],
    ) -> list[ConsumerAgent]:
        committed = deepcopy(snapshot)
        for agent in committed:
            delta = deltas[agent.agent_id]
            agent.state.beliefs.apply(delta.belief_updates)
            agent.state.confidence = clamp01(agent.state.confidence + delta.confidence_delta)
            agent.state.knowledge = clamp01(agent.state.knowledge + delta.knowledge_delta)
            agent.state.product_salience = clamp01(
                agent.state.product_salience + delta.salience_delta
            )
            derive_purchase_intent(agent)
            agent.state.normalize()
        return committed

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
