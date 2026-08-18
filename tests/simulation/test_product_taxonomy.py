import pytest

from simulation.product.knowledge import ProductKnowledge
from simulation.product.semantic_profile import build_product_semantic_profile
from simulation.product.taxonomy import ProductTaxonomy, resolve_product_taxonomy


@pytest.mark.parametrize(
    ("category", "pitch_a", "pitch_b", "expected"),
    [
        (
            "Fitness Technology",
            "Personalized workout app with adaptive coaching.",
            "Monthly service with privacy controls.",
            ProductTaxonomy("fitness_wellness", "fitness_service"),
        ),
        (
            "Smart Home Security",
            "Indoor camera with on-device motion detection.",
            "Camera with optional cloud subscription and local storage.",
            ProductTaxonomy("security_privacy", "indoor_security_camera"),
        ),
        (
            "Personal Finance Software",
            "Budget planner app for household spending.",
            "Finance software with subscription exports.",
            ProductTaxonomy("software_subscription", "finance_software"),
        ),
        (
            "Consumer Audio Electronics",
            "Wireless earbuds controlled from a mobile app.",
            "Premium earbuds with warranty exclusions and difficult returns.",
            ProductTaxonomy("consumer_electronics", "audio_earbuds"),
        ),
        (
            "Beauty and Personal Care Device",
            "LED face device used to study progress in photos.",
            "Skincare hardware with an optional companion app.",
            ProductTaxonomy("personal_care_luxury", "beauty_device"),
        ),
        (
            "Education Technology",
            "Adaptive tutoring platform with monthly subscription.",
            "Study assistant app with AI feedback.",
            ProductTaxonomy("education_productivity", "education_software"),
        ),
        (
            "Food and Meal Planning Software",
            "Meal planning app for families.",
            "Subscription software with grocery-list automation.",
            ProductTaxonomy("software_subscription", "meal_planning_software"),
        ),
        (
            "Cybersecurity Subscription",
            "VPN with privacy controls.",
            "Security app with monthly billing and account controls.",
            ProductTaxonomy("security_privacy", "vpn_service"),
        ),
        (
            "Home Appliance Robotics",
            "Robot vacuum with a mobile app and room mapping.",
            "Home robot with security controls and repair information.",
            ProductTaxonomy("consumer_electronics", "robot_vacuum"),
        ),
        (
            "Business Productivity SaaS",
            "Project boards with enterprise security controls.",
            "Business SaaS with AI summaries and document workflows.",
            ProductTaxonomy("software_subscription", "business_saas"),
        ),
        (
            "Portable Electronics",
            "USB-C power bank for phones.",
            "Portable battery pack with warranty exclusions.",
            ProductTaxonomy("consumer_electronics", "portable_power_bank"),
        ),
        (
            "Luxury Fragrance",
            "Premium eau de parfum.",
            "Luxury perfume with rare-ingredient marketing claims.",
            ProductTaxonomy("personal_care_luxury", "fragrance"),
        ),
    ],
)
def test_recognized_category_is_stable_across_pitch_words(
    category: str,
    pitch_a: str,
    pitch_b: str,
    expected: ProductTaxonomy,
):
    assert resolve_product_taxonomy(category, pitch_a) == expected
    assert resolve_product_taxonomy(category, pitch_b) == expected


def test_unknown_category_can_use_description_as_fallback():
    assert resolve_product_taxonomy(
        "Other",
        "A hardware gadget with a rechargeable battery and electronics enclosure.",
    ).family == "consumer_electronics"


def test_explicit_category_wins_over_conflicting_description():
    taxonomy = resolve_product_taxonomy(
        "Business Productivity SaaS",
        "Security camera privacy controls, fitness tracking, and study workflows are mentioned in examples.",
    )

    assert taxonomy == ProductTaxonomy("software_subscription", "business_saas")


def test_semantic_profile_uses_explicit_category_taxonomy_not_pitch_words():
    product = ProductKnowledge(
        name="FlashBeat",
        category="Consumer Audio Electronics",
        price=7999,
        pitch="Premium earbuds controlled by a subscription app with security settings.",
        features=("wireless audio",),
    )

    profile = build_product_semantic_profile(product)

    assert profile.category_family == "consumer_electronics"
