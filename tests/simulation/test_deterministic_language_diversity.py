from simulation.conversation.background_language import render_background_text
from simulation.conversation.dialogue_realism import DialogueShape, SpeakingStyle
from simulation.population.generator import generate_population


STYLE = SpeakingStyle(
    reasoning="balanced",
    social="balanced",
    confidence="measured",
    detail="moderate",
    receptivity="receptive",
)


def _render_text(*, speaker, listener, topic: str, stance: float, conversation_id: str) -> str:
    return render_background_text(
        speaker=speaker,
        listener=listener,
        topic=topic,
        stance=stance,
        conversation_id=conversation_id,
        dialogue_shape=DialogueShape.uncertainty,
        speaking_style=STYLE,
    )


def test_deterministic_background_composition_is_repeatable_and_diverse():
    speaker, listener = generate_population(2, seed=2026)
    texts = [
        _render_text(
            speaker=speaker,
            listener=listener,
            topic="trust",
            stance=0.04,
            conversation_id=f"conversation-{index}",
        )
        for index in range(100)
    ]
    repeated = [
        _render_text(
            speaker=speaker,
            listener=listener,
            topic="trust",
            stance=0.04,
            conversation_id=f"conversation-{index}",
        )
        for index in range(100)
    ]

    assert texts == repeated
    assert len(set(texts)) >= 4


def test_different_topics_and_stance_bands_remain_fact_bounded():
    speaker, listener = generate_population(2, seed=2027)
    texts = []
    for topic in ("price", "usefulness", "quality", "trust", "novelty", "privacy"):
        for stance in (-0.7, -0.2, 0.0, 0.2, 0.7):
            texts.append(
                _render_text(
                    speaker=speaker,
                    listener=listener,
                    topic=topic,
                    stance=stance,
                    conversation_id=f"{topic}-{stance}",
                )
            )

    joined = " ".join(texts).lower()
    for forbidden in ("competitor", "review", "market average", "free alternative"):
        assert forbidden not in joined
