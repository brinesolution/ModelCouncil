from __future__ import annotations

import hashlib
import math
from collections import defaultdict
from collections.abc import Iterable

import numpy as np

from simulation.audit.logger import RunAuditSink
from simulation.domain.agent import ConsumerAgent
from simulation.domain.consumer_context import SocialMembershipContext


def _stable_seed(seed: int, *parts: object) -> int:
    digest = hashlib.blake2b(
        ":".join(str(part) for part in (seed, *parts)).encode("utf-8"),
        digest_size=8,
    ).digest()
    return int.from_bytes(digest, "big")


def _normalized_key(value: str | None) -> str:
    if not value:
        return "unspecified"
    text = "_".join(str(value).strip().lower().replace("/", " ").split())
    return text or "unspecified"


def _occupation_key(agent: ConsumerAgent) -> str:
    key = _normalized_key(agent.context.occupation.key)
    if key != "unspecified":
        return key
    return _normalized_key(agent.occupation)


def _is_student(agent: ConsumerAgent) -> bool:
    key = _occupation_key(agent)
    return "student" in key


def _city_tier(agent: ConsumerAgent, *, seed: int) -> int:
    rng = np.random.default_rng(_stable_seed(seed, agent.agent_id, "city-tier"))
    score = float(agent.context.demographic.urbanity) + float(rng.normal(0.0, 0.12))
    if score >= 0.70:
        return 1
    if score >= 0.42:
        return 2
    return 3


def _online_interest_categories(agent: ConsumerAgent) -> tuple[str, ...]:
    occupation = _occupation_key(agent)
    values: list[str] = []
    if any(token in occupation for token in ("software", "tech")):
        values.append("technology")
    elif any(token in occupation for token in ("business", "finance", "professional")):
        values.append("business")
    elif any(token in occupation for token in ("health", "medical")):
        values.append("health_wellness")
    elif any(token in occupation for token in ("educator", "student", "teacher")):
        values.append("learning")
    elif any(token in occupation for token in ("creative", "media", "design")):
        values.append("creative_media")
    elif any(token in occupation for token in ("self_employed", "self employed", "entrepreneur")):
        values.append("entrepreneurship")
    else:
        values.append("general_social")

    if (
        agent.context.technology.digital_comfort >= 0.68
        or agent.context.technology.early_adopter >= 0.68
    ):
        values.append("digital_culture")
    if agent.context.social.family_influence >= 0.68:
        values.append("family_community")
    if agent.context.social.influencer_susceptibility >= 0.72:
        values.append("social_trends")

    return tuple(dict.fromkeys(values[:3]))


def _shuffled(items: Iterable[ConsumerAgent], *, seed: int, salt: str) -> list[ConsumerAgent]:
    values = list(items)
    if len(values) < 2:
        return values
    rng = np.random.default_rng(_stable_seed(seed, salt))
    order = rng.permutation(len(values))
    return [values[int(index)] for index in order]


def _chunked_with_sampled_sizes(
    agents: list[ConsumerAgent],
    *,
    seed: int,
    salt: str,
    min_size: int,
    max_size: int,
    center: float,
    sigma: float,
) -> list[list[ConsumerAgent]]:
    shuffled = _shuffled(agents, seed=seed, salt=salt)
    groups: list[list[ConsumerAgent]] = []
    cursor = 0
    group_index = 0
    while cursor < len(shuffled):
        rng = np.random.default_rng(_stable_seed(seed, salt, group_index))
        raw = float(rng.lognormal(mean=math.log(max(center, 1.0)), sigma=sigma))
        size = int(np.clip(round(raw), min_size, max_size))
        group = shuffled[cursor : cursor + size]
        if group:
            groups.append(group)
        cursor += size
        group_index += 1
    return groups


def _household_size_bounds(tendency: str) -> tuple[int, int, float]:
    key = _normalized_key(tendency)
    if "single" in key:
        return 1, 2, 1.35
    if "shared" in key:
        return 2, 3, 2.35
    if "family" in key or "dual" in key:
        return 2, 6, 3.4
    return 1, 4, 2.2


def assign_social_memberships(
    agents: list[ConsumerAgent],
    *,
    seed: int,
    audit: RunAuditSink | None = None,
) -> None:
    """Assign persistent product-independent social memberships in-place.

    Geographic identifiers are abstract synthetic structural cohorts, not real
    locations. Memberships describe represented contacts inside the simulated
    population rather than full real-world household/employer/community size.
    """
    if not agents:
        return

    population_size = len(agents)
    tier_pools: dict[int, list[tuple[str, str]]] = {}
    region_count = max(2, min(8, int(math.ceil(population_size / 800))))
    tier_divisors = {1: 650, 2: 500, 3: 400}
    for tier in (1, 2, 3):
        city_count = max(1, min(18, int(math.ceil(population_size / tier_divisors[tier]))))
        tier_pools[tier] = [
            (
                f"region-{index % region_count:03d}",
                f"city-t{tier}-{index:04d}",
            )
            for index in range(city_count)
        ]

    city_members: dict[str, list[ConsumerAgent]] = defaultdict(list)
    geography: dict[int, tuple[str, str, int]] = {}
    for agent in agents:
        tier = _city_tier(agent, seed=seed)
        pool = tier_pools[tier]
        rng = np.random.default_rng(_stable_seed(seed, agent.agent_id, "city"))
        region_id, city_id = pool[int(rng.integers(0, len(pool)))]
        geography[agent.agent_id] = (region_id, city_id, tier)
        city_members[city_id].append(agent)

    locality_by_agent: dict[int, str] = {}
    for city_id, members in city_members.items():
        shuffled = _shuffled(members, seed=seed, salt=f"locality:{city_id}")
        target_size = 32
        locality_count = max(1, int(math.ceil(len(shuffled) / target_size)))
        for index, agent in enumerate(shuffled):
            locality_index = min(locality_count - 1, index // target_size)
            locality_by_agent[agent.agent_id] = f"{city_id}:locality-{locality_index:03d}"

    household_by_agent: dict[int, str] = {}
    locality_household_buckets: dict[tuple[str, str], list[ConsumerAgent]] = defaultdict(list)
    for agent in agents:
        locality = locality_by_agent[agent.agent_id]
        tendency = _normalized_key(agent.context.demographic.household_tendency)
        locality_household_buckets[(locality, tendency)].append(agent)
    for (locality, tendency), members in locality_household_buckets.items():
        min_size, max_size, center = _household_size_bounds(tendency)
        groups = _chunked_with_sampled_sizes(
            members,
            seed=seed,
            salt=f"household:{locality}:{tendency}",
            min_size=min_size,
            max_size=max_size,
            center=center,
            sigma=0.28,
        )
        for group_index, group in enumerate(groups):
            household_id = f"{locality}:household-{tendency}-{group_index:04d}"
            for agent in group:
                household_by_agent[agent.agent_id] = household_id

    workplace_by_agent: dict[int, str | None] = {agent.agent_id: None for agent in agents}
    workplace_buckets: dict[tuple[str, str], list[ConsumerAgent]] = defaultdict(list)
    for agent in agents:
        if _is_student(agent):
            continue
        _, city_id, _ = geography[agent.agent_id]
        workplace_buckets[(city_id, _occupation_key(agent))].append(agent)
    for (city_id, occupation), members in workplace_buckets.items():
        groups = _chunked_with_sampled_sizes(
            members,
            seed=seed,
            salt=f"workplace:{city_id}:{occupation}",
            min_size=3,
            max_size=30,
            center=10.0,
            sigma=0.55,
        )
        for group_index, group in enumerate(groups):
            workplace_id = f"{city_id}:workplace-{occupation}-{group_index:03d}"
            for agent in group:
                workplace_by_agent[agent.agent_id] = workplace_id

    education_by_agent: dict[int, str | None] = {agent.agent_id: None for agent in agents}
    education_buckets: dict[str, list[ConsumerAgent]] = defaultdict(list)
    for agent in agents:
        if not _is_student(agent):
            continue
        _, city_id, _ = geography[agent.agent_id]
        education_buckets[city_id].append(agent)
    for city_id, members in education_buckets.items():
        groups = _chunked_with_sampled_sizes(
            members,
            seed=seed,
            salt=f"education:{city_id}",
            min_size=8,
            max_size=50,
            center=22.0,
            sigma=0.42,
        )
        for group_index, group in enumerate(groups):
            education_id = f"{city_id}:education-{group_index:03d}"
            for agent in group:
                education_by_agent[agent.agent_id] = education_id

    categories_by_agent = {
        agent.agent_id: _online_interest_categories(agent)
        for agent in agents
    }
    interest_buckets: dict[str, list[ConsumerAgent]] = defaultdict(list)
    for agent in agents:
        for category in categories_by_agent[agent.agent_id]:
            interest_buckets[category].append(agent)
    interest_ids_by_agent: dict[int, list[str]] = defaultdict(list)
    for category, members in interest_buckets.items():
        shuffled = _shuffled(members, seed=seed, salt=f"online:{category}")
        cohort_size = 44
        for index, agent in enumerate(shuffled):
            cohort_index = index // cohort_size
            interest_ids_by_agent[agent.agent_id].append(
                f"online-{category}-{cohort_index:03d}"
            )

    for agent in agents:
        region_id, city_id, city_tier = geography[agent.agent_id]
        agent.context.memberships = SocialMembershipContext(
            region_id=region_id,
            city_id=city_id,
            city_tier=city_tier,
            locality_id=locality_by_agent[agent.agent_id],
            household_id=household_by_agent.get(agent.agent_id),
            workplace_id=workplace_by_agent.get(agent.agent_id),
            education_id=education_by_agent.get(agent.agent_id),
            online_interest_ids=tuple(interest_ids_by_agent.get(agent.agent_id, ())),
        ).normalized()

    if audit is not None:
        household_groups = len({agent.context.memberships.household_id for agent in agents if agent.context.memberships.household_id})
        workplace_groups = len({agent.context.memberships.workplace_id for agent in agents if agent.context.memberships.workplace_id})
        education_groups = len({agent.context.memberships.education_id for agent in agents if agent.context.memberships.education_id})
        online_groups = len({group for agent in agents for group in agent.context.memberships.online_interest_ids})
        audit.emit(
            "population.social_memberships_assigned",
            {
                "version": "social-memberships-v3",
                "population_size": population_size,
                "region_count": len({agent.context.memberships.region_id for agent in agents}),
                "city_count": len({agent.context.memberships.city_id for agent in agents}),
                "locality_count": len({agent.context.memberships.locality_id for agent in agents}),
                "household_group_count": household_groups,
                "workplace_group_count": workplace_groups,
                "education_group_count": education_groups,
                "online_group_count": online_groups,
            },
        )
        for agent in agents:
            audit.emit(
                "population.agent_social_memberships",
                {
                    "agent_id": agent.agent_id,
                    "memberships": agent.context.memberships,
                },
                agent_ids=[agent.agent_id],
            )
