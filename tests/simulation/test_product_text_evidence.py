import pytest

from simulation.product.text_evidence import (
    EvidenceRule,
    normalize_evidence_text,
    phrase_is_affirmed,
    score_rules,
)


@pytest.mark.parametrize(
    ("source", "phrase"),
    [
        ("on-device processing", "on device"),
        ("ON_DEVICE processing", "on-device"),
        ("privacy-preserving local processing", "privacy preserving"),
        ("no-cloud-upload mode", "no cloud upload"),
    ],
)
def test_source_and_rule_phrase_share_the_same_normalization(source: str, phrase: str):
    assert phrase_is_affirmed(source, phrase)


@pytest.mark.parametrize(
    ("source", "phrase"),
    [
        ("no offline map export", "offline"),
        ("not reliable during charging", "reliable"),
        ("never reliable under sustained load", "reliable"),
        ("warranty exclusions apply after opening", "warranty"),
        ("limited warranty with many exclusions", "warranty"),
        ("no local storage is available", "local storage"),
    ],
)
def test_positive_phrase_is_blocked_by_nearby_negative_context(source: str, phrase: str):
    assert not phrase_is_affirmed(source, phrase)


@pytest.mark.parametrize(
    ("source", "phrase"),
    [
        ("works without a cloud subscription", "without a cloud subscription"),
        ("there is no required subscription", "no required subscription"),
        ("no cloud upload; all processing stays on device", "no cloud upload"),
        ("a reliable product with responsive support", "reliable"),
    ],
)
def test_explicit_protective_or_positive_phrase_can_be_affirmed(source: str, phrase: str):
    assert phrase_is_affirmed(source, phrase)


def test_score_rules_uses_context_and_polarity():
    rules = (
        EvidenceRule("reliable", 0.35, "positive"),
        EvidenceRule("unreliable", 0.50, "negative"),
        EvidenceRule("responsive support", 0.30, "positive"),
    )

    assert score_rules("reliable with responsive support", rules) == pytest.approx(0.65)
    assert score_rules("unreliable with responsive support", rules) == pytest.approx(-0.20)
    assert score_rules("not reliable with responsive support", rules) == pytest.approx(0.30)


def test_normalized_text_has_stable_token_boundaries():
    assert normalize_evidence_text("  On-device / AI_powered! ") == "on device ai powered"
