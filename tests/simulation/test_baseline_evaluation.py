from simulation.domain.agent import AgentState, AgentTraits, ConsumerAgent
from simulation.product.baseline_evaluation import evaluate_baseline
from simulation.product.knowledge import ProductKnowledge


def make_agent(
    *,
    price_sensitivity: float = 0.5,
    product_need: float = 0.6,
    technology_adoption: float = 0.6,
    risk_tolerance: float = 0.5,
) -> ConsumerAgent:
    return ConsumerAgent(
        agent_id=1,
        age=25,
        occupation="Test",
        income_score=0.5,
        traits=AgentTraits(
            sociability=0.5,
            price_sensitivity=price_sensitivity,
            technology_adoption=technology_adoption,
            emotionality=0.5,
            logicality=0.5,
            stubbornness=0.5,
            influence_power=0.5,
            product_need=product_need,
            risk_tolerance=risk_tolerance,
            brand_loyalty=0.4,
        ),
        state=AgentState(),
    )


def test_higher_price_sensitivity_penalizes_price_belief():
    low = make_agent(price_sensitivity=0.1)
    high = make_agent(price_sensitivity=0.9)
    product = ProductKnowledge(
        name="Test",
        pitch="Useful subscription service with personalized recommendations.",
        price=999,
        currency="INR",
    )

    low_belief = evaluate_baseline(low, product, seed=1)
    high_belief = evaluate_baseline(high, product, seed=1)

    assert high_belief.price < low_belief.price


def test_higher_product_need_increases_usefulness_belief():
    low = make_agent(product_need=0.1)
    high = make_agent(product_need=0.9)
    product = ProductKnowledge(name="Test", pitch="A useful productivity service.")

    low_belief = evaluate_baseline(low, product, seed=2)
    high_belief = evaluate_baseline(high, product, seed=2)

    assert high_belief.usefulness > low_belief.usefulness


def test_billing_aware_price_belief_distinguishes_cheap_monthly_and_expensive_monthly():
    agent = make_agent(price_sensitivity=0.5, product_need=0.7)
    cheap = ProductKnowledge(
        name="AI Fitness Coach",
        category="Fitness Technology",
        pitch="Personalized workout and nutrition coaching.",
        price=200,
        billing_cadence="monthly",
    )
    expensive = ProductKnowledge(
        name="AI Fitness Coach",
        category="Fitness Technology",
        pitch="Personalized workout and nutrition coaching.",
        price=1500,
        billing_cadence="monthly",
    )
    one_time = ProductKnowledge(
        name="AI Fitness Coach",
        category="Fitness Technology",
        pitch="Personalized workout and nutrition coaching.",
        price=1500,
        billing_cadence="one_time",
    )

    cheap_belief = evaluate_baseline(agent, cheap, seed=17)
    expensive_belief = evaluate_baseline(agent, expensive, seed=17)
    one_time_belief = evaluate_baseline(agent, one_time, seed=17)

    assert cheap_belief.price > 0.10
    assert cheap_belief.price > expensive_belief.price + 0.45
    assert one_time_belief.price > expensive_belief.price + 0.45


def test_baseline_evaluation_is_reproducible_for_same_seed_and_agent():
    agent = make_agent()
    product = ProductKnowledge(name="Test", pitch="A useful productivity service.")

    assert evaluate_baseline(agent, product, seed=10) == evaluate_baseline(agent, product, seed=10)
