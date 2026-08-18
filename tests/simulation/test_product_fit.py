from simulation.domain.agent import AgentState, AgentTraits, ConsumerAgent
from simulation.product.fit import consumer_product_fit
from simulation.product.knowledge import ProductKnowledge
from simulation.product.semantic_profile import build_product_semantic_profile


def _agent(*, occupation: str = "Software Professional", income: float = 0.45, price_sensitivity: float = 0.65, tech: float = 0.75, risk: float = 0.35, need: float = 0.5) -> ConsumerAgent:
    return ConsumerAgent(
        agent_id=7,
        age=31,
        occupation=occupation,
        income_score=income,
        traits=AgentTraits(
            sociability=0.5,
            price_sensitivity=price_sensitivity,
            technology_adoption=tech,
            emotionality=0.4,
            logicality=0.7,
            stubbornness=0.4,
            influence_power=0.5,
            product_need=need,
            risk_tolerance=risk,
            brand_loyalty=0.4,
        ),
        state=AgentState(confidence=0.5),
    )


def _fit(agent: ConsumerAgent, *, category: str, pitch: str, price: float, seed: int = 42):
    product = ProductKnowledge(
        name="Product",
        category=category,
        pitch=pitch,
        price=price,
        currency="INR",
    )
    profile = build_product_semantic_profile(product)
    return consumer_product_fit(agent, product, profile, seed=seed)


def test_category_conditioned_need_differs_for_same_consumer():
    agent = _agent(occupation="Software Professional", tech=0.9, need=0.5)

    software = _fit(
        agent,
        category="Software Productivity",
        pitch="A productivity automation platform with transparent one-time pricing.",
        price=1200,
    )
    luxury = _fit(
        agent,
        category="Luxury Personal Care",
        pitch="A premium perfume for occasional personal use.",
        price=5000,
    )

    assert software.need > luxury.need + 0.08


def test_higher_price_increases_pressure_and_reduces_affordability():
    agent = _agent(income=0.4, price_sensitivity=0.8)
    fair = _fit(
        agent,
        category="Smart Home",
        pitch="A reliable smart lamp with no subscription.",
        price=4000,
    )
    expensive = _fit(
        agent,
        category="Smart Home",
        pitch="A reliable smart lamp with no subscription.",
        price=40000,
    )

    assert expensive.price_pressure > fair.price_pressure + 0.25
    assert expensive.affordability < fair.affordability - 0.15


def test_recurring_cost_adds_burden_at_same_sticker_price():
    agent = _agent()
    one_time = _fit(
        agent,
        category="Software Productivity",
        pitch="A productivity app sold as a one-time purchase with no subscription.",
        price=999,
    )
    recurring = _fit(
        agent,
        category="Software Productivity",
        pitch="A productivity app with a monthly subscription of INR 999.",
        price=999,
    )

    assert recurring.price_pressure > one_time.price_pressure
    assert recurring.affordability < one_time.affordability


def test_higher_income_moderates_price_burden():
    low_income = _agent(income=0.2, price_sensitivity=0.75)
    high_income = _agent(income=0.9, price_sensitivity=0.45)

    low_fit = _fit(
        low_income,
        category="Consumer Electronics",
        pitch="A reliable personal device.",
        price=30000,
    )
    high_fit = _fit(
        high_income,
        category="Consumer Electronics",
        pitch="A reliable personal device.",
        price=30000,
    )

    assert high_fit.affordability > low_fit.affordability + 0.2
    assert high_fit.price_pressure < low_fit.price_pressure


def test_fit_exposes_cadence_aware_price_context_as_canonical_price_state():
    agent = _agent(income=0.55, price_sensitivity=0.55)
    product = ProductKnowledge(
        name="AI Fitness Coach",
        category="Fitness Technology",
        pitch="Personalized coaching billed monthly.",
        price=200,
        currency="INR",
        billing_cadence="monthly",
    )
    profile = build_product_semantic_profile(product)

    fit = consumer_product_fit(agent, product, profile, seed=42)

    assert fit.price_context is not None
    assert fit.price_context.billing_cadence.value == "monthly"
    assert fit.affordability == fit.price_context.affordability
    assert fit.price_pressure == fit.price_context.price_pressure
    assert fit.price_context.stance > 0.15


def test_safety_and_reliability_risk_reduce_consumer_risk_fit():
    agent = _agent(risk=0.35)

    safe = _fit(
        agent,
        category="Portable Electronics",
        pitch="Reliable tested power bank with transparent certification and responsive support.",
        price=2999,
    )
    unsafe = _fit(
        agent,
        category="Portable Electronics",
        pitch=(
            "Power bank with unreliable measured capacity, inconsistent charging, "
            "excessive heat, vague battery certification, and poor replacement support."
        ),
        price=2999,
    )

    assert unsafe.risk_fit < safe.risk_fit - 0.10


def test_fit_is_deterministic_for_same_agent_product_and_seed():
    agent = _agent()
    first = _fit(
        agent,
        category="Fitness Technology",
        pitch="Personalized workout guidance with progress tracking.",
        price=1999,
        seed=91,
    )
    second = _fit(
        agent,
        category="Fitness Technology",
        pitch="Personalized workout guidance with progress tracking.",
        price=1999,
        seed=91,
    )

    assert first == second
