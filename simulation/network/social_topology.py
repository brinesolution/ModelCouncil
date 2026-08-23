from __future__ import annotations

import hashlib
import math
from collections.abc import Mapping
from functools import lru_cache

import numpy as np

from simulation.conversation.models import ConversationPair, ConversationResult
from simulation.domain.agent import ConsumerAgent


def _clip01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _stable_seed(seed: int, agent_id: int, salt: str) -> int:
    digest = hashlib.blake2b(
        f"{seed}:{agent_id}:{salt}".encode("utf-8"),
        digest_size=8,
    ).digest()
    return int.from_bytes(digest, "big")


def social_feature_vector(agent: ConsumerAgent) -> tuple[float, ...]:
    """Persistent social attributes only; product-response fields are excluded."""
    age = _clip01((float(agent.age) - 18.0) / 52.0)
    demographic = agent.context.demographic
    occupation = agent.context.occupation
    social = agent.context.social
    return (
        age,
        _clip01(demographic.urbanity),
        _clip01(agent.traits.sociability),
        _clip01(occupation.tech_exposure),
        _clip01(occupation.time_pressure),
        _clip01(social.peer_influence),
        _clip01(social.family_influence),
        _clip01(social.social_proof),
        _clip01(social.influencer_susceptibility),
    )


def social_engagement(agent: ConsumerAgent) -> float:
    social = agent.context.social
    return _clip01(
        0.62 * agent.traits.sociability
        + 0.14 * social.peer_influence
        + 0.10 * social.social_proof
        + 0.08 * social.influencer_susceptibility
        + 0.06 * (1.0 - agent.context.occupation.time_pressure)
    )


def target_social_degree(
    agent: ConsumerAgent,
    *,
    base_k: int,
    population_size: int,
    seed: int,
) -> int:
    if population_size < 2:
        return 0
    if base_k < 1:
        raise ValueError("base_k must be at least 1")

    engagement = social_engagement(agent)
    social_multiplier = 0.38 + 1.02 * engagement
    sigma = 0.45
    rng = np.random.default_rng(_stable_seed(seed, agent.agent_id, "target-degree"))
    heterogeneity = float(rng.lognormal(mean=-0.5 * sigma * sigma, sigma=sigma))
    raw = base_k * social_multiplier * heterogeneity

    minimum = min(population_size - 1, max(3, int(round(base_k * 0.30))))
    maximum = min(population_size - 1, max(minimum, base_k * 4))
    return int(np.clip(int(round(raw)), minimum, maximum))


@lru_cache(maxsize=16384)
def _normalized_key(value: str | None) -> str:
    if not value:
        return ""
    cleaned = "_".join(value.strip().lower().replace("/", " ").split())
    return "" if cleaned in {"unspecified", "unknown", "none"} else cleaned


def occupation_key(agent: ConsumerAgent) -> str:
    return _normalized_key(agent.context.occupation.key) or _normalized_key(agent.occupation)


def age_band(agent: ConsumerAgent) -> str:
    if agent.age < 25:
        return "18_24"
    if agent.age < 35:
        return "25_34"
    if agent.age < 50:
        return "35_49"
    return "50_plus"


def _same_membership(left_value: str | None, right_value: str | None) -> bool:
    left_key = _normalized_key(left_value)
    right_key = _normalized_key(right_value)
    return bool(left_key and right_key and left_key == right_key)


def explicit_social_layers(left: ConsumerAgent, right: ConsumerAgent) -> tuple[str, ...]:
    left_memberships = left.context.memberships
    right_memberships = right.context.memberships
    layers: list[str] = []
    if _same_membership(left_memberships.household_id, right_memberships.household_id):
        layers.append("household")
    if _same_membership(left_memberships.workplace_id, right_memberships.workplace_id):
        layers.append("workplace")
    if _same_membership(left_memberships.locality_id, right_memberships.locality_id):
        layers.append("local")
    if _same_membership(left_memberships.education_id, right_memberships.education_id):
        layers.append("education")
    if set(left_memberships.online_interest_ids) & set(right_memberships.online_interest_ids):
        layers.append("online")
    return tuple(layers)


def community_overlap(left: ConsumerAgent, right: ConsumerAgent) -> tuple[str, ...]:
    overlap: list[str] = list(explicit_social_layers(left, right))
    if occupation_key(left) and occupation_key(left) == occupation_key(right):
        overlap.append("occupation")
    left_demo = _normalized_key(left.context.demographic.key)
    right_demo = _normalized_key(right.context.demographic.key)
    if left_demo and left_demo == right_demo:
        overlap.append("life_stage")
    left_household = _normalized_key(left.context.demographic.household_tendency)
    right_household = _normalized_key(right.context.demographic.household_tendency)
    if left_household and left_household == right_household:
        overlap.append("household_tendency")
    if age_band(left) == age_band(right):
        overlap.append("age_band")
    if _same_membership(left.context.memberships.city_id, right.context.memberships.city_id):
        overlap.append("city")
    if _same_membership(left.context.memberships.region_id, right.context.memberships.region_id):
        overlap.append("region")
    if _normalized_key(left.primary_language) == _normalized_key(right.primary_language):
        overlap.append("language")
    if _normalized_key(left.locale) == _normalized_key(right.locale):
        overlap.append("locale")
    return tuple(dict.fromkeys(overlap))


RELATIONSHIP_FLOORS: dict[str, float] = {
    "household": 0.55,
    "education": 0.36,
    "workplace": 0.34,
    "local": 0.24,
    "online": 0.18,
    "triadic_closure": 0.15,
    "social_affinity": 0.12,
    "weak_bridge": 0.06,
}


def relationship_floor_for_edge(edge: Mapping[str, object] | dict[str, object]) -> float:
    layers = tuple(str(value) for value in edge.get("social_layers", ()))
    if not layers:
        return 0.0
    return max((RELATIONSHIP_FLOORS.get(layer, 0.0) for layer in layers), default=0.0)


def update_relationship_after_conversation(
    graph: object,
    pair: ConversationPair,
    result: ConversationResult,
    agents_by_id: Mapping[int, ConsumerAgent],
) -> None:
    edge = graph.edges[pair.agent_a_id, pair.agent_b_id]
    stances_by_speaker: dict[int, list[float]] = {
        pair.agent_a_id: [],
        pair.agent_b_id: [],
    }
    for message in result.messages:
        stances_by_speaker.setdefault(message.speaker_id, []).extend(
            float(value) for value in message.topic_effects.values()
        )

    left_values = stances_by_speaker.get(pair.agent_a_id, [])
    right_values = stances_by_speaker.get(pair.agent_b_id, [])
    if left_values and right_values:
        left_mean = float(np.mean(left_values))
        right_mean = float(np.mean(right_values))
        agreement = _clip01(1.0 - abs(left_mean - right_mean) / 2.0)
    else:
        agreement = 0.5

    current_relationship = _clip01(float(edge.get("relationship_strength", 0.4)))
    relationship_delta = 0.0025 + 0.0075 * agreement
    relationship_floor = relationship_floor_for_edge(edge)
    edge["relationship_strength"] = max(
        relationship_floor,
        _clip01(current_relationship + relationship_delta),
    )

    directional = edge.get("directional_trust")
    if isinstance(directional, dict):
        trust_map = {str(key): _clip01(float(value)) for key, value in directional.items()}
    else:
        legacy = _clip01(float(edge.get("trust", 0.4)))
        trust_map = {
            str(pair.agent_a_id): legacy,
            str(pair.agent_b_id): legacy,
        }

    signals: dict[int, list[float]] = {
        pair.agent_a_id: [],
        pair.agent_b_id: [],
    }
    for message in result.messages:
        listener = agents_by_id.get(message.listener_id)
        speaker = agents_by_id.get(message.speaker_id)
        if listener is None or speaker is None:
            continue
        listener_beliefs = listener.state.beliefs.as_dict()
        for topic, stance in message.topic_effects.items():
            current = float(listener_beliefs.get(topic, 0.0))
            topic_agreement = _clip01(1.0 - abs(current - float(stance)) / 2.0)
            speaker_quality = _clip01(
                0.55 * float(message.confidence)
                + 0.45 * float(speaker.state.knowledge)
            )
            signals[message.listener_id].append(
                0.70 * (topic_agreement - 0.5)
                + 0.30 * (speaker_quality - 0.5)
            )

    for truster_id, values in signals.items():
        if not values:
            continue
        key = str(truster_id)
        current_trust = _clip01(float(trust_map.get(key, edge.get("trust", 0.4))))
        trust_delta = 0.010 * float(np.mean(values))
        trust_map[key] = _clip01(current_trust + trust_delta)

    edge["directional_trust"] = trust_map
    if trust_map:
        edge["trust"] = float(np.mean(list(trust_map.values())))


def edge_trust(edge: Mapping[str, object] | dict[str, object], truster_id: int) -> float:
    directional = edge.get("directional_trust")
    if isinstance(directional, dict):
        value = directional.get(str(truster_id), directional.get(truster_id))
        if isinstance(value, (int, float)):
            return _clip01(float(value))
    return _clip01(float(edge.get("trust", 0.4)))


def community_affinity(left: ConsumerAgent, right: ConsumerAgent) -> float:
    explicit = set(explicit_social_layers(left, right))
    explicit_score = (
        0.36 * float("household" in explicit)
        + 0.24 * float("workplace" in explicit)
        + 0.18 * float("local" in explicit)
        + 0.25 * float("education" in explicit)
        + 0.14 * float("online" in explicit)
    )

    left_occ = occupation_key(left)
    right_occ = occupation_key(right)
    occupation_match = 1.0 if left_occ and left_occ == right_occ else 0.0

    left_demo = _normalized_key(left.context.demographic.key)
    right_demo = _normalized_key(right.context.demographic.key)
    life_stage_match = 1.0 if left_demo and left_demo == right_demo else 0.0

    left_household = _normalized_key(left.context.demographic.household_tendency)
    right_household = _normalized_key(right.context.demographic.household_tendency)
    household_tendency_match = 1.0 if left_household and left_household == right_household else 0.0

    age_proximity = math.exp(-abs(float(left.age - right.age)) / 12.0)
    city_match = 1.0 if _same_membership(left.context.memberships.city_id, right.context.memberships.city_id) else 0.0
    region_match = 1.0 if _same_membership(left.context.memberships.region_id, right.context.memberships.region_id) else 0.0
    language_match = 1.0 if _normalized_key(left.primary_language) == _normalized_key(right.primary_language) else 0.0
    locale_match = 1.0 if _normalized_key(left.locale) == _normalized_key(right.locale) else 0.0

    coarse_score = (
        0.08 * occupation_match
        + 0.05 * life_stage_match
        + 0.03 * household_tendency_match
        + 0.08 * age_proximity
        + 0.05 * city_match
        + 0.02 * region_match
        + 0.04 * language_match
        + 0.02 * locale_match
    )
    return _clip01(explicit_score + coarse_score)
