from copy import deepcopy

from simulation.behaviour.purchase import derive_purchase_intent
from simulation.domain.agent import ProductBeliefs
from simulation.domain.consumer_context import DecisionContext, EmotionContext, TechnologyContext
from simulation.population.generator import generate_population
from simulation.product.fit import ConsumerProductFit


def _agent():
    agent = generate_population(2, seed=301)[0]
    agent.state.beliefs = ProductBeliefs(
        price=0.0,
        usefulness=0.0,
        quality=0.0,
        trust=0.0,
        novelty=0.0,
        privacy=0.0,
    )
    return agent


def _fit(
    *,
    need: float = 0.5,
    affordability: float = 0.5,
    price_pressure: float = 0.4,
    privacy_concern: float = 0.5,
    risk_fit: float = 0.5,
) -> ConsumerProductFit:
    return ConsumerProductFit(
        need=need,
        affordability=affordability,
        adoption_fit=0.5,
        risk_fit=risk_fit,
        privacy_concern=privacy_concern,
        price_pressure=price_pressure,
    )


def test_higher_product_need_materially_raises_purchase_intent():
    low = _agent()
    high = deepcopy(low)

    low_value = derive_purchase_intent(low, fit=_fit(need=0.15))
    high_value = derive_purchase_intent(high, fit=_fit(need=0.90))

    assert high_value > low_value + 0.15


def test_negative_trust_penalizes_risk_averse_consumer_more_than_risk_tolerant():
    risk_averse = _agent()
    tolerant = deepcopy(risk_averse)
    risk_averse.traits.risk_tolerance = 0.10
    tolerant.traits.risk_tolerance = 0.90
    risk_averse.state.beliefs.trust = -0.75
    tolerant.state.beliefs.trust = -0.75

    averse_value = derive_purchase_intent(risk_averse, fit=_fit(risk_fit=0.2))
    tolerant_value = derive_purchase_intent(tolerant, fit=_fit(risk_fit=0.8))

    assert tolerant_value > averse_value + 0.08


def test_negative_price_belief_and_pressure_lower_purchase_intent():
    fair = _agent()
    expensive = deepcopy(fair)
    fair.state.beliefs.price = 0.35
    expensive.state.beliefs.price = -0.75

    fair_value = derive_purchase_intent(
        fair,
        fit=_fit(affordability=0.75, price_pressure=0.15),
    )
    expensive_value = derive_purchase_intent(
        expensive,
        fit=_fit(affordability=0.20, price_pressure=0.90),
    )

    assert fair_value > expensive_value + 0.25


def test_negative_privacy_belief_matters_more_for_privacy_concerned_consumer():
    low_concern = _agent()
    high_concern = deepcopy(low_concern)
    low_concern.state.beliefs.privacy = -0.70
    high_concern.state.beliefs.privacy = -0.70

    low_value = derive_purchase_intent(low_concern, fit=_fit(privacy_concern=0.10))
    high_value = derive_purchase_intent(high_concern, fit=_fit(privacy_concern=0.95))

    assert low_value > high_value + 0.05


def test_price_oriented_decision_style_amplifies_price_downside():
    low_price_focus = _agent()
    high_price_focus = deepcopy(low_price_focus)
    low_price_focus.state.beliefs.price = -0.65
    high_price_focus.state.beliefs.price = -0.65
    low_price_focus.context.decision = DecisionContext(price_weight=0.20)
    high_price_focus.context.decision = DecisionContext(price_weight=0.90)

    low_focus_value = derive_purchase_intent(
        low_price_focus,
        fit=_fit(affordability=0.30, price_pressure=0.75),
    )
    high_focus_value = derive_purchase_intent(
        high_price_focus,
        fit=_fit(affordability=0.30, price_pressure=0.75),
    )

    assert low_focus_value > high_focus_value + 0.04


def test_cautious_fear_sensitive_context_amplifies_negative_trust_downside():
    relaxed = _agent()
    cautious = deepcopy(relaxed)
    relaxed.state.beliefs.trust = -0.75
    cautious.state.beliefs.trust = -0.75
    relaxed.context.decision = DecisionContext(evidence_requirement=0.20)
    relaxed.context.emotion = EmotionContext(fear_sensitivity=0.20)
    cautious.context.decision = DecisionContext(evidence_requirement=0.95)
    cautious.context.emotion = EmotionContext(fear_sensitivity=0.90)

    relaxed_value = derive_purchase_intent(relaxed, fit=_fit(risk_fit=0.3))
    cautious_value = derive_purchase_intent(cautious, fit=_fit(risk_fit=0.3))

    assert relaxed_value > cautious_value + 0.02


def test_security_and_privacy_context_amplifies_negative_privacy_downside():
    relaxed = _agent()
    protective = deepcopy(relaxed)
    relaxed.state.beliefs.privacy = -0.75
    protective.state.beliefs.privacy = -0.75
    relaxed.context.emotion = EmotionContext(security_preference=0.20)
    relaxed.context.technology = TechnologyContext(privacy_concern=0.20)
    protective.context.emotion = EmotionContext(security_preference=0.90)
    protective.context.technology = TechnologyContext(privacy_concern=0.90)

    relaxed_value = derive_purchase_intent(relaxed, fit=_fit(privacy_concern=0.8))
    protective_value = derive_purchase_intent(protective, fit=_fit(privacy_concern=0.8))

    assert relaxed_value > protective_value + 0.02


def test_controlled_low_and_high_cases_span_purchase_range():
    low = _agent()
    high = deepcopy(low)
    low.state.beliefs = ProductBeliefs(
        price=-0.9,
        usefulness=-0.8,
        quality=-0.7,
        trust=-0.8,
        novelty=-0.2,
        privacy=-0.8,
    )
    high.state.beliefs = ProductBeliefs(
        price=0.8,
        usefulness=0.9,
        quality=0.8,
        trust=0.8,
        novelty=0.5,
        privacy=0.6,
    )

    low_value = derive_purchase_intent(
        low,
        fit=_fit(need=0.10, affordability=0.10, price_pressure=0.95, privacy_concern=0.9),
    )
    high_value = derive_purchase_intent(
        high,
        fit=_fit(need=0.95, affordability=0.95, price_pressure=0.05, privacy_concern=0.2),
    )

    assert low_value < 0.20
    assert high_value > 0.80
