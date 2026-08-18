from simulation.audit.logger import MemoryRunAuditLogger
from simulation.engine import SimulationConfig, SimulationEngine
from simulation.population.generator import generate_population
from simulation.product.knowledge import ProductKnowledge


FITNESS = ProductKnowledge(
    name="Adaptive AI Fitness Coach",
    category="Fitness Technology",
    pitch=(
        "Personalized workout guidance and progress tracking with a monthly subscription, "
        "clear cancellation, and ordinary privacy controls."
    ),
    price=599,
    currency="INR",
)
BAD_CAMERA = ProductKnowledge(
    name="WatchAll Cloud Camera",
    category="Smart Home Security",
    pitch=(
        "Cloud camera that continuously tracks microphone activity, shares data with advertising partners, "
        "retains data by default, and has no deletion support."
    ),
    price=699,
    currency="INR",
)


def _run(product, *, seed, k, chats, initiators, weak, rounds=5):
    audit = MemoryRunAuditLogger(run_id=f"run-{seed}-{k}-{weak}")
    result = SimulationEngine().run(
        product,
        generate_population(80, seed=seed),
        SimulationConfig(
            rounds=rounds,
            seed=seed,
            k=k,
            max_conversations_per_agent=chats,
            initiator_rate=initiators,
            weak_tie_rate=weak,
        ),
        audit=audit,
    )
    summary = next(event["payload"] for event in audit.events if event["event"] == "social_dynamics.summary")
    return result, audit, summary


def test_high_interaction_produces_more_individual_movement_than_sparse_interaction():
    _, _, sparse = _run(FITNESS, seed=42, k=3, chats=1, initiators=0.20, weak=0.0)
    _, _, dense = _run(FITNESS, seed=42, k=6, chats=3, initiators=0.60, weak=0.25)

    assert dense["mean_absolute_opinion_movement"] > sparse["mean_absolute_opinion_movement"]
    assert dense["median_absolute_opinion_movement"] > sparse["median_absolute_opinion_movement"]


def test_more_weak_ties_increase_cross_cutting_contact_gap_and_actual_weak_exposure():
    _, _, no_weak = _run(FITNESS, seed=43, k=6, chats=2, initiators=0.50, weak=0.0)
    _, _, many_weak = _run(FITNESS, seed=43, k=6, chats=2, initiators=0.50, weak=0.50)

    assert no_weak["selected_weak_tie_share"] == 0.0
    assert many_weak["selected_weak_tie_share"] >= 0.20
    assert many_weak["mean_contact_opinion_gap"] > no_weak["mean_contact_opinion_gap"]


def test_integrated_noise_statistics_meet_phase_gate_and_product_ordering_survives():
    good_result, good_audit, _ = _run(FITNESS, seed=44, k=6, chats=2, initiators=0.50, weak=0.10)
    bad_result, bad_audit, _ = _run(BAD_CAMERA, seed=44, k=6, chats=2, initiators=0.50, weak=0.10)

    events = [
        event["payload"]
        for audit in (good_audit, bad_audit)
        for event in audit.events
        if event["event"] == "aggregation.topic" and abs(event["payload"]["clipped_delta"]) >= 0.003
    ]
    assert len(events) > 100
    noise_exceeds = sum(abs(event["noise_delta"]) > abs(event["clipped_delta"]) for event in events)
    direction_flips = sum(
        event["clipped_delta"] * (event["clipped_delta"] + event["noise_delta"]) < 0
        for event in events
    )

    assert noise_exceeds / len(events) < 0.20
    assert direction_flips / len(events) < 0.08
    assert bad_result.timeline[-1].mean_opinion < good_result.timeline[-1].mean_opinion
    assert bad_result.timeline[-1].mean_purchase_intent < good_result.timeline[-1].mean_purchase_intent
