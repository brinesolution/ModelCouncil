import numpy as np

from simulation.conversation.background_language import _semantic_fallback
from simulation.conversation.dialogue_realism import SpeakingStyle


STYLE = SpeakingStyle(
    reasoning="balanced",
    social="balanced",
    confidence="measured",
    detail="moderate",
    receptivity="receptive",
)


def test_seed_stable_fallback_composition_is_repeatable_and_diverse():
    texts = [
        _semantic_fallback(
            topic="trust",
            stance=0.04,
            rng=np.random.default_rng(10),
            confidence=0.45,
            style=STYLE,
            selector_key=f"conversation-{index}",
        )
        for index in range(400)
    ]
    repeated = [
        _semantic_fallback(
            topic="trust",
            stance=0.04,
            rng=np.random.default_rng(999),
            confidence=0.45,
            style=STYLE,
            selector_key=f"conversation-{index}",
        )
        for index in range(400)
    ]

    assert texts == repeated
    assert len(set(texts)) / len(texts) >= 0.60


def test_different_topics_and_stance_bands_remain_fact_bounded():
    texts = []
    for topic in ("price", "usefulness", "quality", "trust", "novelty", "privacy"):
        for stance in (-0.7, -0.2, 0.0, 0.2, 0.7):
            texts.append(
                _semantic_fallback(
                    topic=topic,
                    stance=stance,
                    rng=np.random.default_rng(1),
                    confidence=0.55,
                    style=STYLE,
                    selector_key=f"{topic}-{stance}",
                )
            )

    joined = " ".join(texts).lower()
    for forbidden in ("competitor", "review", "market average", "free alternative"):
        assert forbidden not in joined
