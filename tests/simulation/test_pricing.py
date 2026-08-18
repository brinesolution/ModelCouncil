from simulation.domain.agent import AgentState, AgentTraits, ConsumerAgent
from simulation.product.knowledge import ProductKnowledge
from simulation.product.pricing import (
    BillingCadence,
    PricePosition,
    build_consumer_price_context,
    resolve_billing_cadence,
)
from simulation.product.semantic_profile import build_product_semantic_profile


def _product(
    *,
    pitch: str,
    category: str = "Fitness Technology",
    billing_cadence: BillingCadence = BillingCadence.auto,
) -> ProductKnowledge:
    return ProductKnowledge(
        name="AI Fitness Coach",
        category=category,
        pitch=pitch,
        price=200,
        currency="INR",
        billing_cadence=billing_cadence,
    )


def test_auto_billing_infers_monthly_yearly_and_one_time_phrases():
    monthly = _product(pitch="Personalized coaching for ₹200 per month.")
    yearly = _product(pitch="Annual subscription billed at ₹4,999 per year.")
    one_time = _product(pitch="One-time purchase with no subscription or recurring fee.")

    assert resolve_billing_cadence(monthly) is BillingCadence.monthly
    assert resolve_billing_cadence(yearly) is BillingCadence.yearly
    assert resolve_billing_cadence(one_time) is BillingCadence.one_time


def test_auto_billing_recognizes_slash_cadence_notation():
    assert resolve_billing_cadence(_product(pitch="AI coaching at ₹200/month.")) is BillingCadence.monthly
    assert resolve_billing_cadence(_product(pitch="AI coaching at ₹2,000/year.")) is BillingCadence.yearly


def test_manual_billing_override_wins_over_pitch_text():
    product = _product(
        pitch="A monthly subscription billed every month.",
        billing_cadence=BillingCadence.one_time,
    )

    assert resolve_billing_cadence(product) is BillingCadence.one_time


def test_auto_default_is_monthly_for_software_service_and_one_time_for_physical_product():
    software = _product(
        pitch="An AI coaching software service with personalized guidance.",
        category="Fitness Software",
    )
    physical = _product(
        pitch="A reliable smart fitness watch with onboard sensors.",
        category="Consumer Electronics",
    )

    assert resolve_billing_cadence(software) is BillingCadence.monthly
    assert resolve_billing_cadence(physical) is BillingCadence.one_time


def test_product_knowledge_exposes_resolved_billing_cadence():
    product = _product(pitch="Personalized coaching with a monthly subscription.")

    assert product.resolved_billing_cadence is BillingCadence.monthly


def _agent(
    *,
    occupation: str = "Software Professional",
    income: float = 0.55,
    price_sensitivity: float = 0.55,
    need: float = 0.65,
) -> ConsumerAgent:
    return ConsumerAgent(
        agent_id=77,
        age=29,
        occupation=occupation,
        income_score=income,
        traits=AgentTraits(
            sociability=0.55,
            price_sensitivity=price_sensitivity,
            technology_adoption=0.75,
            emotionality=0.45,
            logicality=0.70,
            stubbornness=0.40,
            influence_power=0.50,
            product_need=need,
            risk_tolerance=0.55,
            brand_loyalty=0.35,
        ),
        state=AgentState(confidence=0.55),
    )


def _price_context(
    price: float,
    cadence: BillingCadence,
    *,
    agent: ConsumerAgent | None = None,
):
    product = ProductKnowledge(
        name="AI Fitness Coach",
        category="Fitness Technology",
        pitch="AI-powered personalized workouts, nutrition guidance, and progress tracking.",
        price=price,
        currency="INR",
        billing_cadence=cadence,
    )
    profile = build_product_semantic_profile(product)
    resolved_agent = agent or _agent()
    return build_consumer_price_context(
        resolved_agent,
        product,
        category_family=profile.category_family,
        need=resolved_agent.traits.product_need,
    )


def test_fitness_monthly_price_context_changes_continuously_with_amount():
    contexts = [
        _price_context(200, BillingCadence.monthly),
        _price_context(500, BillingCadence.monthly),
        _price_context(900, BillingCadence.monthly),
        _price_context(1500, BillingCadence.monthly),
    ]

    pressures = [context.price_pressure for context in contexts]
    stances = [context.stance for context in contexts]

    assert pressures == sorted(pressures)
    assert stances == sorted(stances, reverse=True)
    assert pressures[1] - pressures[0] > 0.08
    assert pressures[2] - pressures[1] > 0.08
    assert pressures[3] - pressures[2] > 0.08
    assert contexts[0].position in {PricePosition.inexpensive, PricePosition.typical}
    assert contexts[-1].position is PricePosition.expensive


def test_same_1500_amount_is_far_less_burdensome_one_time_than_monthly():
    monthly = _price_context(1500, BillingCadence.monthly)
    one_time = _price_context(1500, BillingCadence.one_time)

    assert monthly.price_pressure > one_time.price_pressure + 0.25
    assert monthly.stance < one_time.stance - 0.30


def test_price_context_does_not_use_occupation_label_as_affordability_proxy():
    student = _agent(occupation="Student")
    executive = _agent(occupation="Senior Executive")

    student_context = _price_context(500, BillingCadence.monthly, agent=student)
    executive_context = _price_context(500, BillingCadence.monthly, agent=executive)

    assert student_context == executive_context


def test_explicit_economic_traits_create_legitimate_price_disagreement():
    constrained = _agent(income=0.18, price_sensitivity=0.90, need=0.40)
    comfortable = _agent(income=0.92, price_sensitivity=0.20, need=0.90)

    constrained_context = _price_context(900, BillingCadence.monthly, agent=constrained)
    comfortable_context = _price_context(900, BillingCadence.monthly, agent=comfortable)

    assert constrained_context.price_pressure > comfortable_context.price_pressure + 0.20
    assert constrained_context.affordability < comfortable_context.affordability - 0.20
    assert constrained_context.stance < comfortable_context.stance - 0.25


def test_product_form_changes_reference_price_within_consumer_electronics():
    agent = _agent(income=0.55, price_sensitivity=0.55, need=0.65)
    power_bank = ProductKnowledge(
        name="Power Bank",
        category="Portable Electronics",
        pitch="Reliable portable USB-C power bank.",
        price=2999,
        currency="INR",
        billing_cadence=BillingCadence.one_time,
    )
    earbuds = ProductKnowledge(
        name="Earbuds",
        category="Consumer Audio Electronics",
        pitch="Reliable wireless earbuds.",
        price=2999,
        currency="INR",
        billing_cadence=BillingCadence.one_time,
    )
    robot = ProductKnowledge(
        name="Robot Vacuum",
        category="Home Appliance Robotics",
        pitch="Reliable robot vacuum.",
        price=2999,
        currency="INR",
        billing_cadence=BillingCadence.one_time,
    )

    power_profile = build_product_semantic_profile(power_bank)
    earbuds_profile = build_product_semantic_profile(earbuds)
    robot_profile = build_product_semantic_profile(robot)
    power_context = build_consumer_price_context(
        agent, power_bank, category_family=power_profile.category_family, need=0.65
    )
    earbuds_context = build_consumer_price_context(
        agent, earbuds, category_family=earbuds_profile.category_family, need=0.65
    )
    robot_context = build_consumer_price_context(
        agent, robot, category_family=robot_profile.category_family, need=0.65
    )

    assert power_context.reference_price_inr < earbuds_context.reference_price_inr < robot_context.reference_price_inr
    assert power_context.price_pressure > earbuds_context.price_pressure > robot_context.price_pressure


def test_low_monthly_price_is_favorable_on_average_without_forcing_every_consumer_positive():
    constrained = _agent(income=0.12, price_sensitivity=0.95, need=0.35)
    comfortable = _agent(income=0.92, price_sensitivity=0.15, need=0.90)

    constrained_context = _price_context(200, BillingCadence.monthly, agent=constrained)
    comfortable_context = _price_context(200, BillingCadence.monthly, agent=comfortable)

    assert comfortable_context.stance > 0.45
    assert constrained_context.stance < 0.15
    assert constrained_context.price_pressure > comfortable_context.price_pressure + 0.25
