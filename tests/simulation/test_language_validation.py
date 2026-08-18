from simulation.conversation.language_validation import validate_rendered_conversation
from simulation.conversation.ledger import ConversationLanguageContext
from simulation.conversation.models import ConversationPair, ConversationResult, SemanticMessage
from simulation.population.generator import generate_population


def _context():
    agents = generate_population(2, seed=801)
    return ConversationLanguageContext.from_agents(agents[0], agents[1])


def _case(topic: str = "price", first_stance: float = 0.75, second_stance: float = 0.20):
    pair = ConversationPair("validation", 1, 0, 1, 0.5)
    result = ConversationResult(
        "validation",
        messages=[
            SemanticMessage(0, 1, {topic: first_stance}, 0.8, 0.7),
            SemanticMessage(1, 0, {topic: second_stance}, 0.7, 0.6),
        ],
    )
    return pair, result


def _validate(text_a: str, text_b: str = "I am still weighing it.", *, topic="price", stance=0.75):
    pair, result = _case(topic, stance)
    return validate_rendered_conversation(
        [
            {"speaker_id": 0, "text": text_a},
            {"speaker_id": 1, "text": text_b},
        ],
        semantic_result=result,
        pair=pair,
        language_context=_context(),
        product_context=None,
    )


def test_rejects_internal_state_leakage():
    for text in (
        "My income score is 0.56, so this looks affordable.",
        "The argument strength is 0.68 and my confidence score is high.",
        "The price context shows a strong negative stance.",
        "My technology adoption and brand loyalty are both high.",
    ):
        result = _validate(text)
        assert not result.valid
        assert any(issue.code == "internal_state_leak" for issue in result.issues)


def test_rejects_visible_speaker_artifacts():
    for text in (
        "A|B: I think the price is fair.",
        "B|A: It seems reasonable.",
        "Agent A: I like the product.",
    ):
        result = _validate(text)
        assert not result.valid
        assert any(issue.code == "speaker_artifact" for issue in result.issues)


def test_rejects_unsupported_reviews_and_specific_alternative_claims():
    for text in (
        "Have you checked the reviews on that?",
        "There are cheaper free alternatives available.",
        "Competitors charge much less for the same thing.",
    ):
        result = _validate(text)
        assert not result.valid
        assert any(issue.code == "unsupported_external_fact" for issue in result.issues)


def test_rejects_demographic_affordability_reasoning():
    result = _validate("As a student, I cannot afford this monthly price.", stance=-0.5)

    assert not result.valid
    assert any(issue.code == "demographic_affordability" for issue in result.issues)


def test_rejects_obvious_price_direction_contradiction():
    favorable = _validate("This price is way too expensive and steep for what it is.", stance=0.78)
    unfavorable = _validate("This is cheap and a great bargain.", stance=-0.78)

    assert not favorable.valid
    assert not unfavorable.valid
    assert any(issue.code == "semantic_direction_contradiction" for issue in favorable.issues)
    assert any(issue.code == "semantic_direction_contradiction" for issue in unfavorable.issues)


def test_rejects_obvious_trust_direction_contradiction_but_allows_nuance():
    bad = _validate("I completely trust these claims and have no doubts.", topic="trust", stance=-0.8)
    nuanced = _validate(
        "I am somewhat cautious about the claims, though I would like more evidence before deciding.",
        topic="trust",
        stance=-0.45,
    )

    assert not bad.valid
    assert nuanced.valid


def test_valid_natural_dialogue_passes():
    result = _validate(
        "For me the price feels reasonable given the stated features, though I would still compare the value carefully.",
        "I can see the value, but I am not fully decided yet.",
        stance=0.55,
    )

    assert result.valid
    assert result.issues == ()
