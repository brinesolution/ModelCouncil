from dataclasses import dataclass

import pytest

from simulation.product.knowledge import ProductKnowledge
from simulation.product.semantic_profile import ProductSemanticProfile, build_product_semantic_profile
from simulation.product.taxonomy import ProductTaxonomy, resolve_product_taxonomy


@dataclass(frozen=True)
class SemanticCase:
    category: str
    expected_taxonomy: ProductTaxonomy
    favorable: str
    premium: str
    problematic: str
    problem_metric: str
    minimum_problem_value: float


CASES = (
    SemanticCase(
        "Fitness Technology",
        ProductTaxonomy("fitness_wellness", "fitness_service"),
        "Personalized workout guidance with progress tracking, transparent cancellation, and local privacy controls.",
        "Adaptive premium coaching with a monthly subscription and detailed analytics.",
        "Fitness service with difficult cancellation, a long commitment, unverified guaranteed results, and retained health data by default.",
        "cancellation_friction",
        0.55,
    ),
    SemanticCase(
        "Smart Home Security",
        ProductTaxonomy("security_privacy", "indoor_security_camera"),
        "Indoor camera with on-device processing, local storage, no cloud upload, and transparent controls.",
        "4K indoor camera with optional cloud features and a warranty.",
        "Cloud camera that continuously tracks microphone activity, shares data with advertising partners, retains data by default, and has no deletion support.",
        "data_practice_risk",
        0.50,
    ),
    SemanticCase(
        "Personal Finance Software",
        ProductTaxonomy("software_subscription", "finance_software"),
        "Budget planner that saves time, exports data, and uses transparent pricing with no hidden fees.",
        "Premium budgeting software with automation and a monthly subscription.",
        "Budget AI with misleading guaranteed savings claims, hidden fees, slow support, and difficult cancellation.",
        "claim_uncertainty",
        0.45,
    ),
    SemanticCase(
        "Consumer Audio Electronics",
        ProductTaxonomy("consumer_electronics", "audio_earbuds"),
        "Reliable durable earbuds with responsive support and clear warranty coverage.",
        "Premium adaptive earbuds with an optional companion app.",
        "Earbuds with frequent connection drops, inconsistent battery life, a sealed battery, limited replacement parts, slow support, and warranty exclusions.",
        "reliability_risk",
        0.50,
    ),
    SemanticCase(
        "Beauty and Personal Care Device",
        ProductTaxonomy("personal_care_luxury", "beauty_device"),
        "Tested skincare device with transparent guidance and a clear return policy.",
        "Premium LED face device with progress tracking.",
        "Miracle LED mask guaranteed to erase visible skin problems without validation, with difficult returns and slow support.",
        "claim_uncertainty",
        0.55,
    ),
    SemanticCase(
        "Education Technology",
        ProductTaxonomy("education_productivity", "education_software"),
        "Adaptive study guidance with progress tracking and transparent pricing.",
        "Premium AI tutoring subscription with automated practice plans.",
        "AI tutor promising guaranteed score improvements without validation, with difficult cancellation and retained student activity data by default.",
        "claim_uncertainty",
        0.55,
    ),
    SemanticCase(
        "Food and Meal Planning Software",
        ProductTaxonomy("software_subscription", "meal_planning_software"),
        "Meal planning software that saves time with grocery-list automation and easy cancellation.",
        "Family meal planning subscription with premium automation.",
        "Meal subscription with a long commitment, difficult cancellation, no self service cancellation, and retained household data after cancellation.",
        "cancellation_friction",
        0.55,
    ),
    SemanticCase(
        "Cybersecurity Subscription",
        ProductTaxonomy("security_privacy", "vpn_service"),
        "VPN with transparent pricing, no hidden fees, and privacy-preserving local controls.",
        "Premium VPN subscription with additional automation and account controls.",
        "VPN that logs browsing metadata, shares usage data with advertising partners, retains records by default, and offers slow deletion support.",
        "data_practice_risk",
        0.50,
    ),
    SemanticCase(
        "Home Appliance Robotics",
        ProductTaxonomy("consumer_electronics", "robot_vacuum"),
        "Reliable tested robot vacuum with durable hardware and responsive support.",
        "Premium robot vacuum with smart mapping and an optional app.",
        "Robot vacuum with frequent failures, unstable mapping, no replacement parts, poor support, and difficult returns.",
        "reliability_risk",
        0.50,
    ),
    SemanticCase(
        "Business Productivity SaaS",
        ProductTaxonomy("software_subscription", "business_saas"),
        "Productivity SaaS that saves time with project automation, transparent pricing, and clear data export.",
        "Premium business SaaS with AI summaries and annual billing.",
        "Business SaaS with unverified productivity claims, default data retention, slow deletion support, hidden fees, and difficult cancellation.",
        "data_practice_risk",
        0.25,
    ),
    SemanticCase(
        "Portable Electronics",
        ProductTaxonomy("consumer_electronics", "portable_power_bank"),
        "Reliable tested power bank with transparent certification and responsive support.",
        "Premium high-capacity power bank with a clear warranty.",
        "Power bank with unreliable measured capacity, inconsistent charging, excessive heat, vague battery certification, poor replacement support, and warranty exclusions.",
        "safety_risk",
        0.45,
    ),
    SemanticCase(
        "Luxury Fragrance",
        ProductTaxonomy("personal_care_luxury", "fragrance"),
        "Well-made fragrance with transparent ingredients and straightforward positioning.",
        "Premium limited-edition fragrance with luxury positioning.",
        "Miracle fragrance with guaranteed attraction claims without validation, misleading scarcity claims, and difficult returns.",
        "claim_uncertainty",
        0.55,
    ),
)


def _profile(category: str, pitch: str, *, name: str) -> ProductSemanticProfile:
    return build_product_semantic_profile(
        ProductKnowledge(
            name=name,
            category=category,
            pitch=pitch,
            price=999,
            currency="INR",
        )
    )


@pytest.mark.parametrize("case", CASES, ids=lambda case: case.expected_taxonomy.form)
def test_phase_2j_a_taxonomy_is_stable_across_product_severity(case: SemanticCase):
    taxonomies = {
        resolve_product_taxonomy(case.category, case.favorable),
        resolve_product_taxonomy(case.category, case.premium),
        resolve_product_taxonomy(case.category, case.problematic),
    }

    assert taxonomies == {case.expected_taxonomy}


@pytest.mark.parametrize("case", CASES, ids=lambda case: case.expected_taxonomy.form)
def test_phase_2j_a_problematic_variant_activates_expected_non_default_risk(case: SemanticCase):
    favorable = _profile(case.category, case.favorable, name=f"{case.expected_taxonomy.form}-good")
    problematic = _profile(case.category, case.problematic, name=f"{case.expected_taxonomy.form}-bad")

    problem_value = getattr(problematic, case.problem_metric)
    favorable_value = getattr(favorable, case.problem_metric)

    assert problem_value >= case.minimum_problem_value
    assert problem_value > favorable_value


def test_phase_2j_a_known_problematic_products_do_not_receive_false_positive_trust():
    for case in CASES:
        if case.expected_taxonomy.form not in {"audio_earbuds", "portable_power_bank", "vpn_service"}:
            continue
        problematic = _profile(case.category, case.problematic, name=f"{case.expected_taxonomy.form}-bad")
        assert problematic.trust_evidence < 0
