from pathlib import Path

from simulation.audit.logger import MemoryRunAuditLogger
from simulation.population.excel_repository import ExcelTraitRepository
from simulation.population.generator import generate_population


TRAIT_ROOT = Path("data/traits")


def test_excel_population_samples_and_activates_rich_context_profiles():
    repository = ExcelTraitRepository(TRAIT_ROOT)
    audit = MemoryRunAuditLogger(run_id="activation")

    agents = generate_population(120, seed=1201, traits=repository, audit=audit)

    assert any(agent.context.archetype_key != "unspecified" for agent in agents)
    assert any(agent.context.decision.key != "unspecified" for agent in agents)
    assert any(agent.context.emotion.key != "unspecified" for agent in agents)
    assert any(agent.context.behaviour.research_tendency != 0.5 for agent in agents)
    assert any(agent.context.technology.ai_familiarity != 0.5 for agent in agents)
    assert any(agent.context.social.peer_influence != 0.5 for agent in agents)

    generated = [event for event in audit.events if event["event"] == "population.agent_generated"]
    assert generated
    for event in generated:
        sources = event["payload"]["sampled_sources"]
        assert set(sources) >= {
            "demographic",
            "archetype",
            "occupation",
            "personality",
            "economic",
            "social",
            "technology",
            "consumer_behaviour",
            "decision_style",
            "emotion",
        }
        assert event["payload"]["agent"]["context"]["archetype_key"] == sources["archetype"]["key"]


def test_active_context_fields_are_bounded_and_profile_keys_are_retained():
    repository = ExcelTraitRepository(TRAIT_ROOT)
    agents = generate_population(200, seed=1202, traits=repository)

    for agent in agents:
        context = agent.context
        assert context.demographic.key != "unspecified"
        assert context.decision.key != "unspecified"
        assert context.emotion.key != "unspecified"
        assert 0 <= context.demographic.urbanity <= 1
        assert all(
            0 <= value <= 1
            for value in (
                context.decision.logic_weight,
                context.decision.emotion_weight,
                context.decision.social_weight,
                context.decision.price_weight,
                context.decision.decision_speed,
                context.decision.evidence_requirement,
                context.emotion.optimism,
                context.emotion.fear_sensitivity,
                context.emotion.excitement_sensitivity,
                context.emotion.fomo,
                context.emotion.status_motivation,
                context.emotion.security_preference,
                context.emotion.reactance,
                context.behaviour.switching_tendency,
                context.behaviour.research_tendency,
                context.behaviour.quality_sensitivity,
                context.behaviour.convenience_preference,
                context.behaviour.review_trust,
                context.behaviour.purchase_frequency,
                context.technology.ai_familiarity,
                context.technology.ai_trust,
                context.technology.privacy_concern,
                context.technology.digital_comfort,
                context.technology.early_adopter,
                context.social.peer_influence,
                context.social.family_influence,
                context.social.social_proof,
                context.social.influencer_susceptibility,
                context.social.message_accuracy,
            )
        )
