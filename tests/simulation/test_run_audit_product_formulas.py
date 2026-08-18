import pytest

from simulation.audit.logger import MemoryRunAuditLogger
from simulation.population.generator import generate_population
from simulation.product.baseline_evaluation import evaluate_baseline
from simulation.product.fit import consumer_product_fit
from simulation.product.knowledge import ProductKnowledge
from simulation.product.semantic_profile import build_product_semantic_profile


def _product() -> ProductKnowledge:
    return ProductKnowledge(
        name="AI Fitness Coach",
        category="Fitness Technology",
        pitch="AI-powered personalized workouts and progress tracking for a monthly subscription.",
        price=500,
        currency="INR",
        billing_cadence="monthly",
    )


def test_product_profile_and_consumer_fit_are_audited_with_resolved_price_context():
    audit = MemoryRunAuditLogger(run_id="product")
    product = _product()
    agent = generate_population(2, seed=17)[0]

    profile = build_product_semantic_profile(product, audit=audit)
    fit = consumer_product_fit(agent, product, profile, seed=17, audit=audit)

    profile_events = [event for event in audit.events if event["event"] == "product.semantic_profile"]
    assert len(profile_events) == 1
    assert profile_events[0]["payload"]["product_name"] == product.name
    assert profile_events[0]["payload"]["profile"]["category_family"] == profile.category_family

    price_events = [event for event in audit.events if event["event"] == "consumer.price_context"]
    assert len(price_events) == 1
    price_payload = price_events[0]["payload"]
    assert price_payload["formula_version"] == "consumer-price-context-v2h"
    assert sum(price_payload["components"]["pressure"].values()) == pytest.approx(
        price_payload["pressure_raw"]
    )
    assert sum(price_payload["components"]["affordability"].values()) == pytest.approx(
        price_payload["affordability_raw"]
    )
    assert sum(price_payload["components"]["stance"].values()) == pytest.approx(
        price_payload["stance_raw"]
    )

    fit_events = [event for event in audit.events if event["event"] == "consumer.fit"]
    assert len(fit_events) == 1
    payload = fit_events[0]["payload"]
    assert payload["agent_id"] == agent.agent_id
    assert payload["result"]["need"] == pytest.approx(fit.need)
    assert payload["result"]["affordability"] == pytest.approx(fit.affordability)
    assert payload["result"]["price_pressure"] == pytest.approx(fit.price_pressure)
    assert payload["result"]["price_context"]["billing_cadence"] == "monthly"
    assert payload["result"]["price_context"]["reference_price_inr"] > 0
    assert "idiosyncratic_need" in payload["components"]
    for component_name in ("need", "adoption_fit", "privacy_concern", "risk_fit"):
        assert component_name in payload["formula_components"]


def test_baseline_topic_formula_components_recombine_to_logged_results():
    audit = MemoryRunAuditLogger(run_id="baseline")
    product = _product()
    agent = generate_population(2, seed=29)[0]
    profile = build_product_semantic_profile(product)
    fit = consumer_product_fit(agent, product, profile, seed=29)

    beliefs = evaluate_baseline(agent, product, 29, profile=profile, fit=fit, audit=audit)

    topic_events = [event for event in audit.events if event["event"] == "baseline.topic_evaluation"]
    assert len(topic_events) == 6
    by_topic = {event["payload"]["topic"]: event["payload"] for event in topic_events}
    for topic, expected in beliefs.as_dict().items():
        payload = by_topic[topic]
        assert payload["formula_version"].startswith("baseline-")
        assert sum(payload["components"].values()) == pytest.approx(payload["raw_value"])
        assert payload["result"] == pytest.approx(expected)
        assert -1.0 <= payload["result"] <= 1.0

    completed = [event for event in audit.events if event["event"] == "baseline.completed"]
    assert len(completed) == 1
    assert completed[0]["payload"]["beliefs"] == pytest.approx(beliefs.as_dict())
