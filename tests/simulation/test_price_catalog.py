from simulation.product.price_catalog import reference_price_for_taxonomy
from simulation.product.pricing import BillingCadence
from simulation.product.taxonomy import ProductTaxonomy


def test_electronics_forms_have_distinct_one_time_reference_prices():
    earbuds = reference_price_for_taxonomy(
        ProductTaxonomy("consumer_electronics", "audio_earbuds"),
        BillingCadence.one_time,
    )
    power_bank = reference_price_for_taxonomy(
        ProductTaxonomy("consumer_electronics", "portable_power_bank"),
        BillingCadence.one_time,
    )
    robot = reference_price_for_taxonomy(
        ProductTaxonomy("consumer_electronics", "robot_vacuum"),
        BillingCadence.one_time,
    )

    assert power_bank < earbuds < robot


def test_personal_care_forms_do_not_share_one_reference():
    beauty_device = reference_price_for_taxonomy(
        ProductTaxonomy("personal_care_luxury", "beauty_device"),
        BillingCadence.one_time,
    )
    fragrance = reference_price_for_taxonomy(
        ProductTaxonomy("personal_care_luxury", "fragrance"),
        BillingCadence.one_time,
    )

    assert beauty_device != fragrance


def test_unknown_form_uses_family_fallback():
    reference = reference_price_for_taxonomy(
        ProductTaxonomy("consumer_electronics", "unknown_form"),
        BillingCadence.one_time,
    )

    assert reference == 12000.0


def test_same_taxonomy_and_cadence_is_stable():
    taxonomy = ProductTaxonomy("software_subscription", "business_saas")

    assert reference_price_for_taxonomy(taxonomy, BillingCadence.monthly) == reference_price_for_taxonomy(
        taxonomy,
        BillingCadence.monthly,
    )
