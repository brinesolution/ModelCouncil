from statistics import mean

from simulation.behaviour.purchase import BELIEF_IMPORTANCE
from simulation.engine import SimulationConfig, SimulationEngine
from simulation.population.generator import generate_population
from simulation.product.baseline_evaluation import evaluate_baseline
from simulation.product.fit import consumer_product_fit
from simulation.product.knowledge import ProductKnowledge
from simulation.product.semantic_profile import build_product_semantic_profile


def _product(*, pitch: str, category: str = "Consumer Electronics", price: float = 3499) -> ProductKnowledge:
    return ProductKnowledge(
        name="Scenario Product",
        category=category,
        pitch=pitch,
        price=price,
        currency="INR",
    )


def _baseline_means(product: ProductKnowledge, *, seed: int = 73, size: int = 220) -> dict[str, float]:
    agents = generate_population(size, seed=seed)
    profile = build_product_semantic_profile(product)
    beliefs = []
    for agent in agents:
        fit = consumer_product_fit(agent, product, profile, seed=seed)
        beliefs.append(
            evaluate_baseline(
                agent,
                product,
                seed=seed,
                profile=profile,
                fit=fit,
            )
        )
    result = {
        topic: mean(getattr(item, topic) for item in beliefs)
        for topic in ("price", "usefulness", "quality", "trust", "novelty", "privacy")
    }
    result["opinion"] = sum(BELIEF_IMPORTANCE[topic] * result[topic] for topic in BELIEF_IMPORTANCE)
    return result


def test_reliable_supported_product_baseline_differs_materially_from_bad_product():
    good = _baseline_means(
        _product(
            pitch="A useful reliable durable device with responsive customer support, warranty coverage, transparent pricing, and proven convenience."
        )
    )
    bad = _baseline_means(
        _product(
            pitch="An unnecessary unreliable fragile device with frequent failures, poor support, hidden fees, misleading claims, and little value."
        )
    )

    assert good["quality"] > bad["quality"] + 0.40
    assert good["trust"] > bad["trust"] + 0.35
    assert good["usefulness"] > bad["usefulness"] + 0.25
    assert good["opinion"] > bad["opinion"] + 0.20


def test_privacy_heavy_product_creates_more_negative_privacy_belief_than_local_product():
    tracking = _baseline_means(
        _product(
            category="Security Privacy",
            price=1499,
            pitch="A cloud service that continuously tracks location and microphone activity and uploads personal health data.",
        )
    )
    local = _baseline_means(
        _product(
            category="Security Privacy",
            price=1499,
            pitch="A useful privacy-preserving service that runs locally and offline, keeps data on-device, and requires no cloud upload.",
        )
    )

    assert local["privacy"] > tracking["privacy"] + 0.30
    assert local["trust"] > tracking["trust"] + 0.15


def test_category_relative_price_changes_price_belief_materially():
    fair = _baseline_means(
        _product(
            category="Smart Home",
            price=4000,
            pitch="A useful reliable smart lamp with transparent one-time pricing and no subscription.",
        )
    )
    expensive = _baseline_means(
        _product(
            category="Smart Home",
            price=40000,
            pitch="A useful reliable smart lamp with transparent one-time pricing and no subscription.",
        )
    )

    assert fair["price"] > expensive["price"] + 0.30


def _final_engine_metrics(product: ProductKnowledge, *, seed: int = 91, size: int = 120):
    population = generate_population(size, seed=seed)
    result = SimulationEngine().run(
        product,
        population,
        SimulationConfig(
            rounds=2,
            seed=seed,
            k=6,
            max_conversations_per_agent=1,
            initiator_rate=0.30,
            weak_tie_rate=0.05,
        ),
    )
    return result.timeline[-1]


def test_same_seed_unreliable_earbuds_score_below_reliable_earbuds():
    fair = _final_engine_metrics(
        _product(
            category="Consumer Audio Electronics",
            price=7999,
            pitch="Reliable durable earbuds with responsive support and clear warranty coverage.",
        ),
        seed=600,
    )
    bad = _final_engine_metrics(
        _product(
            category="Consumer Audio Electronics",
            price=7999,
            pitch=(
                "Earbuds with frequent connection drops, inconsistent battery life, a sealed battery, "
                "limited replacement parts, slow support, warranty exclusions, and difficult returns."
            ),
        ),
        seed=600,
    )

    assert bad.mean_opinion < fair.mean_opinion - 0.10
    assert bad.mean_purchase_intent < fair.mean_purchase_intent - 0.04


def test_same_seed_invasive_camera_scores_below_local_privacy_preserving_camera():
    local = _final_engine_metrics(
        _product(
            category="Smart Home Security",
            price=3499,
            pitch="Indoor camera with on-device processing, local storage, no cloud upload, and transparent controls.",
        ),
        seed=601,
    )
    invasive = _final_engine_metrics(
        _product(
            category="Smart Home Security",
            price=3499,
            pitch=(
                "Cloud camera that continuously tracks microphone activity, shares data with advertising partners, "
                "retains data by default, and has no deletion support."
            ),
        ),
        seed=601,
    )

    assert invasive.mean_opinion < local.mean_opinion - 0.08
    assert invasive.mean_purchase_intent < local.mean_purchase_intent - 0.04


def test_same_seed_unsafe_power_bank_scores_below_reliable_power_bank():
    safe = _final_engine_metrics(
        _product(
            category="Portable Electronics",
            price=2999,
            pitch="Reliable tested power bank with transparent certification and responsive support.",
        ),
        seed=602,
    )
    unsafe = _final_engine_metrics(
        _product(
            category="Portable Electronics",
            price=2999,
            pitch=(
                "Power bank with unreliable measured capacity, inconsistent charging, excessive heat, "
                "vague battery certification, poor replacement support, and warranty exclusions."
            ),
        ),
        seed=602,
    )

    assert unsafe.mean_opinion < safe.mean_opinion - 0.10
    assert unsafe.mean_purchase_intent < safe.mean_purchase_intent - 0.04


def test_full_engine_is_product_sensitive_before_any_llm_rendering():
    population = generate_population(180, seed=29)
    config = SimulationConfig(
        rounds=2,
        seed=29,
        k=8,
        max_conversations_per_agent=2,
        initiator_rate=0.20,
        weak_tie_rate=0.05,
    )
    good_product = _product(
        pitch="A useful reliable durable device with responsive customer support, warranty coverage, transparent pricing, and proven convenience."
    )
    bad_product = _product(
        pitch="An unnecessary unreliable fragile device with frequent failures, poor support, hidden fees, misleading claims, and little value."
    )

    good = SimulationEngine().run(good_product, population, config)
    bad = SimulationEngine().run(bad_product, population, config)

    assert good.timeline[0].mean_opinion > bad.timeline[0].mean_opinion + 0.18
    assert good.timeline[-1].mean_opinion > bad.timeline[-1].mean_opinion + 0.18
    assert good.timeline[-1].positive_share > bad.timeline[-1].positive_share
    assert bad.timeline[-1].negative_share > 0
