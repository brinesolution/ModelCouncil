from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True, slots=True)
class ProductTaxonomy:
    family: str
    form: str


_EXPLICIT_CATEGORY_RULES: tuple[tuple[tuple[str, ...], ProductTaxonomy], ...] = (
    (("consumer audio", "audio electronics", "earbud", "headphone"), ProductTaxonomy("consumer_electronics", "audio_earbuds")),
    (("portable electronics", "power bank", "battery pack"), ProductTaxonomy("consumer_electronics", "portable_power_bank")),
    (("home appliance robotics", "robot vacuum", "robotics"), ProductTaxonomy("consumer_electronics", "robot_vacuum")),
    (("smart home security", "security camera"), ProductTaxonomy("security_privacy", "indoor_security_camera")),
    (("smart home productivity", "smart home"), ProductTaxonomy("smart_home", "smart_home_device")),
    (("beauty and personal care", "personal care device", "skincare device"), ProductTaxonomy("personal_care_luxury", "beauty_device")),
    (("luxury fragrance", "fragrance", "perfume"), ProductTaxonomy("personal_care_luxury", "fragrance")),
    (("luxury personal care",), ProductTaxonomy("personal_care_luxury", "personal_care")),
    (("education technology", "education software", "learning technology", "education productivity"), ProductTaxonomy("education_productivity", "education_software")),
    (("business productivity saas", "productivity saas"), ProductTaxonomy("software_subscription", "business_saas")),
    (("personal finance software", "budgeting software", "finance software"), ProductTaxonomy("software_subscription", "finance_software")),
    (("food and meal planning software", "meal planning software"), ProductTaxonomy("software_subscription", "meal_planning_software")),
    (("cybersecurity subscription", "vpn service", "vpn subscription", "vpn security privacy"), ProductTaxonomy("security_privacy", "vpn_service")),
    (("fitness technology", "fitness software", "fitness service"), ProductTaxonomy("fitness_wellness", "fitness_service")),
)


def resolve_product_taxonomy(
    category: str,
    descriptive_text: str = "",
) -> ProductTaxonomy:
    """Resolve a stable numerical taxonomy from explicit category first.

    Once an explicit category matches a known rule, descriptive text cannot
    change the family/form. Text is only a fallback for unknown/general
    categories.
    """
    normalized_category = _normalize(category)
    for aliases, taxonomy in _EXPLICIT_CATEGORY_RULES:
        if any(_contains_phrase(normalized_category, alias) for alias in aliases):
            return taxonomy

    return _fallback_taxonomy(descriptive_text)


def _fallback_taxonomy(text: str) -> ProductTaxonomy:
    source = _normalize(text)
    if any(_contains_phrase(source, phrase) for phrase in ("vpn", "cybersecurity")):
        return ProductTaxonomy("security_privacy", "security_service")
    if any(_contains_phrase(source, phrase) for phrase in ("security camera", "indoor camera")):
        return ProductTaxonomy("security_privacy", "indoor_security_camera")
    if any(_contains_phrase(source, phrase) for phrase in ("fitness", "workout", "health coach")):
        return ProductTaxonomy("fitness_wellness", "fitness_service")
    if any(_contains_phrase(source, phrase) for phrase in ("perfume", "fragrance")):
        return ProductTaxonomy("personal_care_luxury", "fragrance")
    if any(_contains_phrase(source, phrase) for phrase in ("skincare", "beauty device", "face device")):
        return ProductTaxonomy("personal_care_luxury", "beauty_device")
    if any(_contains_phrase(source, phrase) for phrase in ("robot vacuum", "robotic vacuum")):
        return ProductTaxonomy("consumer_electronics", "robot_vacuum")
    if any(_contains_phrase(source, phrase) for phrase in ("earbud", "headphone")):
        return ProductTaxonomy("consumer_electronics", "audio_earbuds")
    if any(_contains_phrase(source, phrase) for phrase in ("power bank", "battery pack")):
        return ProductTaxonomy("consumer_electronics", "portable_power_bank")
    if any(_contains_phrase(source, phrase) for phrase in ("hardware", "electronics", "device", "gadget")):
        return ProductTaxonomy("consumer_electronics", "general_electronics")
    if any(_contains_phrase(source, phrase) for phrase in ("education", "tutor", "learning", "study assistant")):
        return ProductTaxonomy("education_productivity", "education_software")
    if any(_contains_phrase(source, phrase) for phrase in ("saas", "software", "app", "subscription", "platform")):
        return ProductTaxonomy("software_subscription", "software_service")
    return ProductTaxonomy("general", "general")


def _normalize(text: str) -> str:
    compact = re.sub(r"[^a-z0-9]+", " ", str(text).lower())
    return " ".join(compact.split())


def _contains_phrase(text: str, phrase: str) -> bool:
    normalized_phrase = _normalize(phrase)
    return f" {normalized_phrase} " in f" {text} "
