import pytest

from simulation.product.knowledge import ProductKnowledge
from simulation.product.semantic_profile import build_product_semantic_profile


def _product(*, name: str = "Test Product", category: str = "General", pitch: str, price: float = 3499) -> ProductKnowledge:
    return ProductKnowledge(
        name=name,
        category=category,
        pitch=pitch,
        price=price,
        currency="INR",
    )


def test_semantic_profile_is_deterministic_and_bounded():
    product = _product(
        category="Smart Home",
        pitch="A smart adaptive lamp with reliable hardware, local controls, and no subscription.",
    )

    first = build_product_semantic_profile(product)
    second = build_product_semantic_profile(product)

    assert first == second
    for value in (
        first.usefulness_evidence,
        first.quality_evidence,
        first.trust_evidence,
        first.novelty_evidence,
        first.support_reliability,
    ):
        assert -1.0 <= value <= 1.0
    for value in (
        first.privacy_exposure,
        first.complexity,
        first.recurring_cost,
        first.claim_uncertainty,
    ):
        assert 0.0 <= value <= 1.0
    assert first.reference_price_inr > 0


def test_reliable_supportive_pitch_scores_above_unreliable_poor_support_pitch():
    good = build_product_semantic_profile(
        _product(
            category="Consumer Electronics",
            pitch="Reliable durable hardware with responsive customer support, warranty coverage, and transparent pricing.",
        )
    )
    bad = build_product_semantic_profile(
        _product(
            category="Consumer Electronics",
            pitch="An unreliable fragile device with frequent failures, poor support, hidden fees, and misleading claims.",
        )
    )

    assert good.quality_evidence > bad.quality_evidence + 0.5
    assert good.trust_evidence > bad.trust_evidence + 0.5
    assert good.support_reliability > bad.support_reliability + 0.7
    assert bad.claim_uncertainty > good.claim_uncertainty


def test_privacy_heavy_tracking_scores_more_exposed_than_local_offline_pitch():
    tracking = build_product_semantic_profile(
        _product(
            category="Security / Privacy",
            pitch="Cloud service continuously tracks location, microphone activity, personal data, and uploads health data.",
        )
    )
    local = build_product_semantic_profile(
        _product(
            category="Security / Privacy",
            pitch="Runs locally and offline, keeps data on-device, requires no cloud upload, and is privacy preserving.",
        )
    )

    assert tracking.privacy_exposure > local.privacy_exposure + 0.5
    assert local.trust_evidence > tracking.trust_evidence


def test_warranty_exclusions_do_not_create_positive_trust_or_support():
    profile = build_product_semantic_profile(
        _product(
            category="Consumer Audio Electronics",
            pitch="Unreliable earbuds with slow support and warranty exclusions after opening.",
            price=7999,
        )
    )

    assert profile.quality_evidence < 0
    assert profile.support_reliability <= 0
    assert profile.trust_evidence <= 0


def test_on_device_hyphenation_is_recognized_as_privacy_protective():
    hyphenated = build_product_semantic_profile(
        _product(
            category="Smart Home Security",
            pitch="On-device processing with no cloud upload and local storage.",
        )
    )
    spaced = build_product_semantic_profile(
        _product(
            category="Smart Home Security",
            pitch="On device processing with no cloud upload and local storage.",
        )
    )

    assert hyphenated.privacy_exposure == pytest.approx(spaced.privacy_exposure)
    assert hyphenated.trust_evidence == pytest.approx(spaced.trust_evidence)


def test_without_cloud_subscription_is_not_treated_as_required_recurring_cost():
    profile = build_product_semantic_profile(
        _product(
            category="Smart Home Security",
            pitch="The camera works without a cloud subscription and stores video locally.",
            price=3499,
        )
    )

    assert profile.recurring_cost <= 0.10


def test_unreliable_unserviceable_earbuds_create_material_risk_signals():
    profile = build_product_semantic_profile(
        _product(
            category="Consumer Audio Electronics",
            pitch=(
                "Premium wireless earbuds with frequent connection drops, inconsistent battery life, "
                "a sealed battery, limited replacement parts, slow customer support, warranty exclusions, "
                "and difficult returns after opening."
            ),
            price=7999,
        )
    )

    assert profile.reliability_risk >= 0.50
    assert profile.serviceability_risk >= 0.35
    assert profile.quality_evidence < -0.20
    assert profile.support_reliability < 0
    assert profile.trust_evidence < 0


def test_privacy_contradictory_vpn_creates_data_practice_and_trust_risk():
    profile = build_product_semantic_profile(
        _product(
            category="Cybersecurity Subscription",
            pitch=(
                "VPN service that logs browsing metadata, shares usage data with advertising partners, "
                "retains records by default, and provides slow deletion support."
            ),
            price=299,
        )
    )

    assert profile.data_practice_risk >= 0.50
    assert profile.privacy_exposure >= 0.55
    assert profile.trust_evidence < 0


def test_overheating_power_bank_creates_safety_and_reliability_risk():
    profile = build_product_semantic_profile(
        _product(
            category="Portable Electronics",
            pitch=(
                "Power bank with unreliable measured capacity, inconsistent charging, excessive heat during fast charging, "
                "vague battery certification, poor replacement support, and warranty exclusions."
            ),
            price=2999,
        )
    )

    assert profile.reliability_risk >= 0.50
    assert profile.safety_risk >= 0.45
    assert profile.quality_evidence < -0.30
    assert profile.trust_evidence < 0


def test_lock_in_meal_plan_creates_cancellation_friction():
    profile = build_product_semantic_profile(
        _product(
            category="Food and Meal Planning Software",
            pitch=(
                "Meal planning subscription with a long commitment, difficult cancellation, no self-service cancellation, "
                "and retained household data after cancellation."
            ),
            price=899,
        )
    )

    assert profile.cancellation_friction >= 0.55
    assert profile.trust_evidence < 0


def test_miracle_claim_creates_claim_uncertainty():
    profile = build_product_semantic_profile(
        _product(
            category="Beauty and Personal Care Device",
            pitch="A miracle LED mask guaranteed to erase visible skin problems in seven days without validation.",
            price=9999,
        )
    )

    assert profile.claim_uncertainty >= 0.55
    assert profile.trust_evidence < 0


def test_no_subscription_is_not_misclassified_as_recurring_cost():
    one_time = build_product_semantic_profile(
        _product(
            category="Software Productivity",
            pitch="A useful productivity app sold as a one-time purchase with no subscription and no recurring fee.",
            price=999,
        )
    )
    monthly = build_product_semantic_profile(
        _product(
            category="Software Productivity",
            pitch="A useful productivity app with a monthly subscription and recurring fee.",
            price=999,
        )
    )

    assert one_time.recurring_cost <= 0.10
    assert monthly.recurring_cost >= 0.70


def test_recurring_cost_novelty_and_complexity_are_detected():
    profile = build_product_semantic_profile(
        _product(
            category="Software Productivity",
            pitch="An AI-powered adaptive automation platform requiring an account, app setup, integrations, and a monthly subscription.",
            price=999,
        )
    )

    assert profile.category_family == "software_subscription"
    assert profile.recurring_cost >= 0.7
    assert profile.novelty_evidence > 0.2
    assert profile.complexity > 0.3


@pytest.mark.parametrize(
    ("category", "expected"),
    [
        ("Fitness Technology", "fitness_wellness"),
        ("Smart Home / Productivity", "smart_home"),
        ("Education Productivity", "education_productivity"),
        ("Luxury Personal Care", "personal_care_luxury"),
        ("VPN Security Privacy", "security_privacy"),
    ],
)
def test_category_family_classification(category: str, expected: str):
    profile = build_product_semantic_profile(
        _product(category=category, pitch="A straightforward product description with transparent pricing.")
    )
    assert profile.category_family == expected
