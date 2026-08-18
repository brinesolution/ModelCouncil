from simulation.domain.agent import AgentTraits, ConsumerAgent
from simulation.domain.consumer_context import (
    BehaviourContext,
    ConsumerContext,
    DecisionContext,
    DemographicContext,
    EmotionContext,
    SocialContext,
    TechnologyContext,
)


def _traits() -> AgentTraits:
    return AgentTraits(
        sociability=0.5,
        price_sensitivity=0.5,
        technology_adoption=0.5,
        emotionality=0.5,
        logicality=0.5,
        stubbornness=0.5,
        influence_power=0.5,
        product_need=0.5,
        risk_tolerance=0.5,
        brand_loyalty=0.5,
    )


def test_consumer_agent_remains_backward_compatible_without_explicit_context():
    agent = ConsumerAgent(
        agent_id=1,
        age=30,
        occupation="Education",
        income_score=0.5,
        traits=_traits(),
    )

    assert agent.context.demographic.key == "unspecified"
    assert agent.context.decision.key == "unspecified"
    assert agent.context.emotion.key == "unspecified"


def test_explicit_consumer_context_retains_active_profile_fields():
    context = ConsumerContext(
        demographic=DemographicContext(
            key="urban_parent",
            urbanity=0.88,
            household_tendency="family with children",
        ),
        decision=DecisionContext(
            key="analytical_buyer",
            logic_weight=0.9,
            emotion_weight=0.2,
            social_weight=0.28,
            price_weight=0.68,
            decision_speed=0.3,
            evidence_requirement=0.88,
        ),
        emotion=EmotionContext(
            key="cautious_emotional",
            optimism=0.42,
            fear_sensitivity=0.72,
            excitement_sensitivity=0.42,
            fomo=0.36,
            status_motivation=0.3,
            security_preference=0.82,
            reactance=0.4,
        ),
        behaviour=BehaviourContext(
            switching_tendency=0.46,
            research_tendency=0.94,
            quality_sensitivity=0.82,
            convenience_preference=0.48,
            review_trust=0.72,
            purchase_frequency=0.42,
        ),
        technology=TechnologyContext(
            ai_familiarity=0.78,
            ai_trust=0.64,
            privacy_concern=0.46,
            digital_comfort=0.92,
            early_adopter=0.70,
        ),
        social=SocialContext(
            peer_influence=0.52,
            family_influence=0.52,
            social_proof=0.54,
            influencer_susceptibility=0.44,
            message_accuracy=0.82,
        ),
        archetype_key="practical_family_buyer",
    )

    agent = ConsumerAgent(
        agent_id=2,
        age=38,
        occupation="Education",
        income_score=0.6,
        traits=_traits(),
        context=context,
    )

    assert agent.context == context
    assert agent.context.demographic.household_tendency == "family with children"
    assert agent.context.decision.evidence_requirement == 0.88
    assert agent.context.technology.digital_comfort == 0.92


def test_context_normalized_clamps_numeric_fields_without_changing_labels():
    context = ConsumerContext(
        demographic=DemographicContext(key="x", urbanity=1.4, household_tendency="couple"),
        decision=DecisionContext(key="y", logic_weight=1.2, price_weight=-0.2),
        emotion=EmotionContext(key="z", fear_sensitivity=1.5, optimism=-0.1),
        technology=TechnologyContext(ai_trust=2.0),
    ).normalized()

    assert context.demographic.key == "x"
    assert context.demographic.urbanity == 1.0
    assert context.decision.logic_weight == 1.0
    assert context.decision.price_weight == 0.0
    assert context.emotion.fear_sensitivity == 1.0
    assert context.emotion.optimism == 0.0
    assert context.technology.ai_trust == 1.0
