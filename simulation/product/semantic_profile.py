from __future__ import annotations

from dataclasses import dataclass
import re

import numpy as np

from simulation.product.knowledge import ProductKnowledge
from simulation.product.price_catalog import reference_price_for_taxonomy
from simulation.product.taxonomy import resolve_product_taxonomy
from simulation.product.text_evidence import phrase_is_affirmed
from simulation.audit.logger import RunAuditSink


@dataclass(frozen=True, slots=True)
class ProductSemanticProfile:
    category_family: str
    usefulness_evidence: float
    quality_evidence: float
    trust_evidence: float
    novelty_evidence: float
    privacy_exposure: float
    complexity: float
    recurring_cost: float
    support_reliability: float
    claim_uncertainty: float
    reliability_risk: float
    serviceability_risk: float
    safety_risk: float
    data_practice_risk: float
    cancellation_friction: float
    reference_price_inr: float


_USEFUL_POSITIVE = {
    "saves time": 0.35,
    "save time": 0.35,
    "automates": 0.28,
    "automation": 0.24,
    "personalized": 0.25,
    "guidance": 0.18,
    "tracking": 0.14,
    "productivity": 0.24,
    "convenience": 0.22,
    "progress tracking": 0.22,
    "focus controls": 0.16,
}
_USEFUL_NEGATIVE = {
    "limited use": 0.45,
    "limited usefulness": 0.55,
    "unnecessary": 0.50,
    "no benefit": 0.60,
    "inconvenient": 0.35,
    "little value": 0.45,
}
_QUALITY_POSITIVE = {
    "durable": 0.35,
    "reliable": 0.35,
    "premium": 0.20,
    "tested": 0.20,
    "high quality": 0.35,
    "well built": 0.30,
}
_QUALITY_NEGATIVE = {
    "unreliable": 0.50,
    "fragile": 0.40,
    "frequent failures": 0.60,
    "frequent failure": 0.55,
    "poor quality": 0.60,
    "breaks often": 0.55,
    "defective": 0.55,
}
_TRUST_POSITIVE = {
    "transparent pricing": 0.35,
    "no hidden fees": 0.35,
    "warranty": 0.26,
    "responsive customer support": 0.35,
    "responsive support": 0.32,
    "privacy preserving": 0.28,
    "on-device": 0.22,
    "runs locally": 0.22,
    "offline": 0.18,
}
_TRUST_NEGATIVE = {
    "poor support": 0.55,
    "hidden fees": 0.55,
    "misleading": 0.55,
    "unverified": 0.35,
    "frequent failures": 0.35,
    "frequent failure": 0.32,
    "data selling": 0.55,
}
_SUPPORT_POSITIVE = {
    "responsive customer support": 0.50,
    "responsive support": 0.48,
    "warranty": 0.35,
    "reliable": 0.30,
    "durable": 0.22,
}
_SUPPORT_NEGATIVE = {
    "poor support": 0.65,
    "no support": 0.60,
    "unreliable": 0.45,
    "frequent failures": 0.60,
    "frequent failure": 0.55,
    "fragile": 0.30,
}
_PRIVACY_RISK = {
    "camera": 0.18,
    "microphone": 0.22,
    "location": 0.22,
    "personal data": 0.24,
    "health data": 0.30,
    "biometric": 0.28,
    "cloud upload": 0.30,
    "uploads": 0.16,
    "tracking": 0.16,
    "continuously tracks": 0.34,
}
_PRIVACY_PROTECTIVE = {
    "runs locally": 0.34,
    "local processing": 0.32,
    "offline": 0.30,
    "on-device": 0.32,
    "no cloud upload": 0.40,
    "privacy preserving": 0.36,
    "keeps data on-device": 0.40,
}
_NOVELTY_POSITIVE = {
    "ai-powered": 0.28,
    "ai powered": 0.28,
    " artificial intelligence ": 0.24,
    "smart": 0.18,
    "adaptive": 0.22,
    "automatic": 0.16,
    "automation": 0.16,
    "augmented": 0.18,
    "agentic": 0.22,
    "new": 0.10,
    "novel": 0.20,
}
_COMPLEXITY = {
    "requires an account": 0.28,
    "account required": 0.28,
    "requiring an account": 0.28,
    "requires app": 0.24,
    "app setup": 0.26,
    "setup": 0.18,
    "configuration": 0.22,
    "integration": 0.18,
    "integrations": 0.24,
    "multiple devices": 0.22,
}
_RECURRING = {
    "monthly subscription": 0.72,
    "annual subscription": 0.72,
    "subscription": 0.48,
    "per month": 0.52,
    "per year": 0.48,
    "recurring": 0.44,
    "monthly fee": 0.55,
    "annual fee": 0.52,
}
_NON_RECURRING = {
    "no subscription": 0.90,
    "no required subscription": 0.95,
    "no recurring fee": 0.90,
    "no recurring fees": 0.90,
    "one time purchase": 0.60,
    "one time payment": 0.60,
    "without a cloud subscription": 0.95,
    "without subscription": 0.90,
}
_UNCERTAINTY = {
    "unverified": 0.45,
    "without validation": 0.35,
    "no validation": 0.35,
    "claims to": 0.18,
    "promises to": 0.18,
    "guaranteed": 0.24,
    "miracle": 0.45,
    "misleading": 0.50,
    "frequent failures": 0.20,
    "poor support": 0.15,
}
_RELIABILITY_RISK = {
    "frequent connection drops": 0.45,
    "connection drops": 0.30,
    "inconsistent battery life": 0.35,
    "unreliable measured capacity": 0.45,
    "inconsistent charging": 0.40,
    "frequent failures": 0.55,
    "frequent failure": 0.50,
    "unreliable": 0.40,
    "unstable": 0.35,
    "disconnects": 0.30,
}
_SERVICEABILITY_RISK = {
    "sealed battery": 0.35,
    "limited replacement parts": 0.35,
    "no replacement parts": 0.50,
    "difficult returns": 0.30,
    "slow customer support": 0.25,
    "slow support": 0.25,
    "poor replacement support": 0.35,
    "no repair": 0.45,
    "not repairable": 0.45,
    "warranty exclusions": 0.30,
}
_SAFETY_RISK = {
    "excessive heat": 0.55,
    "overheating": 0.60,
    "unsafe": 0.60,
    "vague battery certification": 0.35,
    "uncertified": 0.45,
    "fire risk": 0.60,
    "battery hazard": 0.60,
}
_DATA_PRACTICE_RISK = {
    "logs browsing metadata": 0.45,
    "logs usage data": 0.35,
    "shares usage data": 0.45,
    "shares data": 0.35,
    "advertising partners": 0.30,
    "sells data": 0.60,
    "data selling": 0.60,
    "retains records by default": 0.35,
    "retains data by default": 0.35,
    "retained household data after cancellation": 0.35,
    "slow deletion support": 0.25,
    "no deletion": 0.50,
    "cannot delete": 0.50,
    "default upload": 0.35,
}
_CANCELLATION_FRICTION = {
    "long commitment": 0.35,
    "difficult cancellation": 0.45,
    "no self service cancellation": 0.35,
    "no cancellation": 0.55,
    "lock in": 0.40,
    "annual commitment": 0.25,
}


def build_product_semantic_profile(
    product: ProductKnowledge,
    *,
    audit: RunAuditSink | None = None,
) -> ProductSemanticProfile:
    text = _normalize(" ".join((product.category, product.pitch, *product.features)))
    taxonomy = resolve_product_taxonomy(
        product.category,
        " ".join((product.pitch, *product.features)),
    )
    family = taxonomy.family

    usefulness = _signed_signal(text, _USEFUL_POSITIVE, _USEFUL_NEGATIVE)
    base_quality = _signed_signal(text, _QUALITY_POSITIVE, _QUALITY_NEGATIVE)
    base_trust = _signed_signal(text, _TRUST_POSITIVE, _TRUST_NEGATIVE)
    base_support = _signed_signal(text, _SUPPORT_POSITIVE, _SUPPORT_NEGATIVE)
    novelty = _positive_signal(text, _NOVELTY_POSITIVE)
    privacy_risk = _positive_signal(text, _PRIVACY_RISK)
    privacy_protection = _positive_signal(text, _PRIVACY_PROTECTIVE)
    complexity = _clip01(_positive_signal(text, _COMPLEXITY))
    recurring = _clip01(
        _positive_signal(text, _RECURRING)
        - _positive_signal(text, _NON_RECURRING)
    )
    uncertainty = _clip01(_positive_signal(text, _UNCERTAINTY))
    reliability_risk = _clip01(_positive_signal(text, _RELIABILITY_RISK))
    serviceability_risk = _clip01(_positive_signal(text, _SERVICEABILITY_RISK))
    safety_risk = _clip01(_positive_signal(text, _SAFETY_RISK))
    data_practice_risk = _clip01(_positive_signal(text, _DATA_PRACTICE_RISK))
    cancellation_friction = _clip01(_positive_signal(text, _CANCELLATION_FRICTION))

    quality = _clip_opinion(
        base_quality
        - 0.55 * reliability_risk
        - 0.30 * serviceability_risk
        - 0.45 * safety_risk
    )
    support = _clip_opinion(
        base_support
        - 0.25 * reliability_risk
        - 0.45 * serviceability_risk
    )
    privacy_exposure = _clip01(
        0.10
        + privacy_risk
        + 0.65 * data_practice_risk
        - 0.85 * privacy_protection
    )
    trust = _clip_opinion(
        base_trust
        + 0.20 * privacy_protection
        - 0.18 * privacy_risk
        - 0.30 * reliability_risk
        - 0.30 * serviceability_risk
        - 0.50 * safety_risk
        - 0.55 * data_practice_risk
        - 0.30 * cancellation_friction
        - 0.35 * uncertainty
    )

    profile = ProductSemanticProfile(
        category_family=family,
        usefulness_evidence=usefulness,
        quality_evidence=quality,
        trust_evidence=trust,
        novelty_evidence=novelty,
        privacy_exposure=privacy_exposure,
        complexity=complexity,
        recurring_cost=recurring,
        support_reliability=support,
        claim_uncertainty=uncertainty,
        reliability_risk=reliability_risk,
        serviceability_risk=serviceability_risk,
        safety_risk=safety_risk,
        data_practice_risk=data_practice_risk,
        cancellation_friction=cancellation_friction,
        reference_price_inr=reference_price_for_taxonomy(
            taxonomy,
            product.resolved_billing_cadence,
        ),
    )
    if audit is not None:
        audit.emit(
            "product.semantic_profile",
            {
                "product_name": product.name,
                "category": product.category,
                "category_family": taxonomy.family,
                "product_form": taxonomy.form,
                "billing_cadence": product.resolved_billing_cadence,
                "profile": profile,
            },
        )
    return profile


def _normalize(text: str) -> str:
    compact = re.sub(r"[^a-z0-9₹%+]+", " ", text.lower())
    return f" {' '.join(compact.split())} "


def _contains(text: str, phrase: str) -> bool:
    return phrase_is_affirmed(text, phrase)


def _score_matches(text: str, phrases: dict[str, float]) -> float:
    return sum(weight for phrase, weight in phrases.items() if _contains(text, phrase))


def _signed_signal(
    text: str,
    positive: dict[str, float],
    negative: dict[str, float],
) -> float:
    pos = _score_matches(text, positive)
    neg = _score_matches(text, negative)
    return _clip_opinion(pos - neg)


def _positive_signal(text: str, phrases: dict[str, float]) -> float:
    return _clip01(_score_matches(text, phrases))


def _category_family(category: str, text: str) -> str:
    category_text = _normalize(category)
    source = f"{category_text} {text}"
    if any(token in source for token in (" vpn ", " security ", " privacy ", " cybersecurity ")):
        return "security_privacy"
    if any(token in source for token in (" fitness ", " wellness ", " workout ", " health coach ")):
        return "fitness_wellness"
    if any(token in source for token in (" smart home ", " home automation ", " smart lamp ", " smart light ")):
        return "smart_home"
    if any(token in source for token in (" education ", " learning ", " study ", " productivity ")):
        if " software " not in source and " saas " not in source and " subscription " not in source:
            return "education_productivity"
    if any(token in source for token in (" luxury ", " perfume ", " personal care ", " beauty ", " skincare ")):
        return "personal_care_luxury"
    if any(token in source for token in (" software ", " saas ", " platform ", " app ", " subscription ")):
        return "software_subscription"
    if any(token in source for token in (" electronics ", " device ", " gadget ", " hardware ")):
        return "consumer_electronics"
    return "general"


def _clip01(value: float) -> float:
    return float(np.clip(value, 0.0, 1.0))


def _clip_opinion(value: float) -> float:
    return float(np.clip(value, -1.0, 1.0))
