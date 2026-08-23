from __future__ import annotations

import hashlib

from simulation.conversation.dialogue_realism import (
    DialogueShape,
    SpeakingStyle,
    derive_speaking_style,
    stance_band,
)
from simulation.conversation.ledger import AgentLanguageProfile
from simulation.domain.agent import ConsumerAgent
from simulation.product.pricing import BillingCadence, ConsumerPriceContext


_TOPIC_TEMPLATES: dict[str, dict[str, tuple[str, ...]]] = {
    "usefulness": {
        "strong_negative": (
            "I do not see enough practical value in this for me.",
            "This does not solve a problem I care enough about to use regularly.",
            "For my needs, the usefulness feels too limited to matter much.",
        ),
        "moderate_negative": (
            "I am not convinced I would use this often enough to matter.",
            "I can understand the idea, but the practical value still feels limited for me.",
            "There is some purpose here, but not enough to make it compelling for me.",
        ),
        "mild_negative": (
            "I can see some use for it, though I am not sure it fits my routine.",
            "It has a purpose, but I am only slightly unconvinced about how useful it would be for me.",
            "I would probably use only part of what it offers.",
        ),
        "neutral": (
            "I can see possible uses, but I am still undecided about how much they matter to me.",
            "The usefulness could go either way for me depending on normal day-to-day use.",
            "I understand the intended value, but I have not formed a strong view on it.",
        ),
        "mild_positive": (
            "This could be useful for me if it fits naturally into my routine.",
            "I can see a practical benefit here, even if it is not essential for me.",
            "There is enough useful value that I would consider trying it.",
        ),
        "moderate_positive": (
            "This looks genuinely useful for the way I would use it.",
            "The practical benefit is one of the stronger parts of the product for me.",
            "I can see this saving me effort or helping me stay more consistent.",
        ),
        "strong_positive": (
            "This fits a real need for me and I can see myself using it often.",
            "The usefulness is very clear to me; this solves something I actually care about.",
            "For my needs, the practical value is one of the main reasons I would want it.",
        ),
    },
    "quality": {
        "strong_negative": (
            "I have serious doubts about whether the quality would hold up for me.",
            "The quality side is a major concern for me right now.",
            "I would be very reluctant to rely on it given how I currently view the quality.",
        ),
        "moderate_negative": (
            "I am not very confident about the quality yet.",
            "The quality does not feel convincing enough for me at the moment.",
            "I would hesitate because I am still fairly doubtful about the quality.",
        ),
        "mild_negative": (
            "I have a few quality concerns, though they are not deal-breakers yet.",
            "I am slightly cautious about the quality and would want more confidence before deciding.",
            "The quality feels a little uncertain to me, rather than clearly bad.",
        ),
        "neutral": (
            "I do not have a strong quality judgment yet.",
            "The quality could be fine, but I would need more experience before deciding.",
            "I am fairly neutral on the quality at this point.",
        ),
        "mild_positive": (
            "The quality sounds reasonably promising to me.",
            "I am leaning positive on the quality, though not strongly yet.",
            "Nothing about the quality worries me much at this stage.",
        ),
        "moderate_positive": (
            "I feel fairly confident about the quality based on what is presented.",
            "The quality is one of the parts I feel good about.",
            "I would be reasonably comfortable with the quality as described.",
        ),
        "strong_positive": (
            "I have a very strong impression of the quality here.",
            "The quality is a major positive for me.",
            "I would feel highly confident about the quality based on the information I have.",
        ),
    },
    "trust": {
        "strong_negative": (
            "I am very skeptical and would not trust the claims without much stronger evidence.",
            "Trust is a major problem for me here.",
            "I would be extremely cautious because I do not feel confident in the claims right now.",
        ),
        "moderate_negative": (
            "I am fairly skeptical and would want clearer evidence before trusting it.",
            "I do not fully trust the claims yet.",
            "The trust side still gives me meaningful reservations.",
        ),
        "mild_negative": (
            "I have some trust concerns, but I am not dismissing it outright.",
            "I am a little cautious about the claims and would want them explained clearly.",
            "My trust is slightly on the negative side for now.",
        ),
        "neutral": (
            "I am keeping an open mind until I have enough evidence to trust it either way.",
            "I do not have a strong trust judgment yet.",
            "I would want clearer evidence before becoming confident or skeptical.",
        ),
        "mild_positive": (
            "I am leaning toward trusting it, though I would still keep a little caution.",
            "The claims feel reasonably credible to me so far.",
            "I have a mildly positive level of trust in what is being presented.",
        ),
        "moderate_positive": (
            "I feel reasonably comfortable trusting the product as described.",
            "The trust side looks fairly solid to me.",
            "I am more confident than skeptical about the claims here.",
        ),
        "strong_positive": (
            "I feel very confident about the trust side of this product.",
            "Trust is one of the strongest positives for me here.",
            "I have a high level of confidence in the claims as they are presented.",
        ),
    },
    "novelty": {
        "strong_negative": (
            "The newness feels more like friction than a benefit for me.",
            "I am strongly put off by how unfamiliar this feels.",
            "The novelty does not appeal to me; I would rather use something more familiar.",
        ),
        "moderate_negative": (
            "I am not particularly drawn to the novelty here.",
            "The newness makes me somewhat cautious rather than excited.",
            "I would need a practical reason before the novelty felt worthwhile to me.",
        ),
        "mild_negative": (
            "The newness makes me a little cautious, but not strongly opposed.",
            "I am slightly hesitant about the unfamiliar parts.",
            "Novelty alone does not add much value for me.",
        ),
        "neutral": (
            "The newness is interesting, but it does not move me strongly either way.",
            "I am neutral about the novelty until I see whether it matters in normal use.",
            "Being new is neither a major positive nor a major concern for me.",
        ),
        "mild_positive": (
            "The newness is interesting enough that I would take a closer look.",
            "I like that it feels a little different, as long as it remains practical.",
            "The novelty is a small positive for me.",
        ),
        "moderate_positive": (
            "I find the newer approach genuinely appealing.",
            "The novelty makes me more interested in trying it.",
            "I like the newer direction, especially if it works smoothly in practice.",
        ),
        "strong_positive": (
            "The novelty is a major part of what attracts me to this.",
            "I am very interested precisely because it feels new and different.",
            "The newer approach is one of the strongest positives for me.",
        ),
    },
    "privacy": {
        "strong_negative": (
            "The privacy implications are a serious concern for me.",
            "I would be very uncomfortable with the privacy side as I currently understand it.",
            "Privacy is close to a deal-breaker for me here.",
        ),
        "moderate_negative": (
            "I have meaningful privacy concerns and would want much clearer controls.",
            "The privacy side makes me fairly uncomfortable.",
            "I would hesitate because I am not comfortable enough with how data is handled.",
        ),
        "mild_negative": (
            "I have a few privacy concerns, though they are not overwhelming.",
            "I am slightly uneasy about the privacy side and would check the controls carefully.",
            "Privacy is a modest concern for me right now.",
        ),
        "neutral": (
            "I would check the privacy details before deciding either way.",
            "I am neutral on privacy until I know more about the controls.",
            "The privacy side is something I would check, but I do not have a strong view yet.",
        ),
        "mild_positive": (
            "The privacy side seems reasonably acceptable to me.",
            "I am mildly comfortable with the privacy approach as described.",
            "Privacy does not look like a major obstacle for me.",
        ),
        "moderate_positive": (
            "I feel fairly comfortable with the privacy approach.",
            "The privacy handling is a meaningful positive for me.",
            "I like the level of control suggested by the privacy approach.",
        ),
        "strong_positive": (
            "The privacy approach gives me a lot of confidence.",
            "Privacy is one of the strongest reasons I feel positive about this.",
            "I am very comfortable with the privacy setup as described.",
        ),
    },
}


_PRICE_TEMPLATES: dict[str, tuple[str, ...]] = {
    "strong_negative": (
        "The {cadence} cost is more than I would be comfortable paying for this.",
        "For me, the {cadence} commitment is too high to justify right now.",
        "I would hesitate mainly because the {cadence} price puts too much pressure on my budget.",
        "The {cadence} price is a serious obstacle for me.",
        "At this level, the {cadence} cost would make me walk away unless my need changed a lot.",
    ),
    "moderate_negative": (
        "The {cadence} cost feels high for me relative to how much I expect to use it.",
        "I would have to think carefully before taking on this {cadence} price.",
        "Price is a meaningful concern for me at this {cadence} level.",
        "The {cadence} commitment is higher than I would prefer.",
        "I like parts of the product, but this {cadence} price would still make me hesitate.",
    ),
    "mild_negative": (
        "The {cadence} cost is a little higher than I would prefer, though not a deal-breaker.",
        "I am slightly cautious about the {cadence} price.",
        "The {cadence} commitment gives me some hesitation, but I could still consider it.",
        "Price is a small concern for me at this level.",
        "I would want to be sure I use it enough before feeling comfortable with the {cadence} cost.",
    ),
    "neutral": (
        "I am still weighing whether the {cadence} cost matches the value I would get from it.",
        "The {cadence} price feels neither especially good nor especially bad to me.",
        "I could go either way on the {cadence} cost depending on how useful it becomes for me.",
        "Price is not settled for me yet; I would weigh it against how often I use the product.",
        "I am fairly neutral about the {cadence} price at this point.",
    ),
    "mild_positive": (
        "The {cadence} price seems reasonably manageable for me.",
        "I am fairly comfortable with the {cadence} cost if I end up using the product regularly.",
        "The {cadence} price feels acceptable to me rather than burdensome.",
        "I can see the {cadence} cost fitting my budget if the product proves useful to me.",
        "Price is a small positive for me at this {cadence} level.",
    ),
    "moderate_positive": (
        "The {cadence} price looks quite reasonable for what I expect to get from it.",
        "I feel comfortable with the {cadence} cost given my level of interest in the product.",
        "The {cadence} price is easy for me to justify if I use it consistently.",
        "I see the {cadence} cost as manageable and broadly good value for my needs.",
        "I do not have much price resistance at this {cadence} level.",
    ),
    "strong_positive": (
        "The {cadence} price feels very manageable for me.",
        "I see the {cadence} cost as a strong positive given how relevant the product is to me.",
        "At this {cadence} price, cost would barely hold me back.",
        "The {cadence} commitment is comfortably within what I would consider paying.",
        "Price is one of the easier parts of this decision for me at this level.",
    ),
}


_REPLY_DISAGREEMENT = (
    "I see that differently.",
    "That's where I disagree.",
    "I don't see that the same way.",
    "I'm not convinced by that.",
)

_REPLY_AGREEMENT = (
    "That is also my concern.",
    "I am with you on that point.",
    "I see that much the same way.",
    "Yes, that part stands out to me too.",
)

_REPLY_TRANSITION = (
    "That is one part of it.",
    "I would add another concern.",
    "There is another side I am weighing.",
    "I am also thinking about a different part of it.",
)

_SHAPE_FOLLOW_UP = {
    DialogueShape.agreement: "I can see why someone with similar priorities would land in a similar place.",
    DialogueShape.partial_agreement: "I agree with part of the case, though I would still weigh the details differently.",
    DialogueShape.challenge: "I would push back if the opposite view were treated as obvious.",
    DialogueShape.trade_off: "For me, that has to be weighed against the other parts of the product.",
    DialogueShape.concession: "I can see the other side, but it does not fully change my view.",
    DialogueShape.uncertainty: "I would want a bit more evidence before settling on it.",
    DialogueShape.priority_comparison: "That matters to me, but it is not the only thing I would base the decision on.",
}

_SEMANTIC_OPENERS = (
    "",
    "At this point, ",
    "Right now, ",
    "For me, ",
    "Based on what I know, ",
    "As I weigh it, ",
    "My current read is that ",
    "The way I see it, ",
    "On balance, ",
    "So far, ",
    "For this decision, ",
    "From where I stand, ",
    "Looking at that part alone, ",
    "When I focus on that point, ",
    "My reaction for now is that ",
    "Taking the product as described, ",
)

_MEASURED_CLOSERS = (
    "",
    "That is where I am landing for now.",
    "I could still move if clearer evidence changes the picture.",
    "It is one part of the decision rather than the whole decision.",
    "I would keep weighing that against the rest of the product.",
    "I am not treating that point as settled forever.",
    "That view could strengthen or weaken with more concrete information.",
    "I would want the rest of the product to support that impression.",
    "That is my current position rather than a final verdict.",
    "I would still compare that concern with the practical benefits.",
    "I am keeping some room to revise that view.",
    "That factor matters, but it does not decide everything by itself.",
)

_LOW_CONFIDENCE_CLOSERS = (
    "",
    "I would want more evidence before treating that as settled.",
    "My view could change quite a bit with clearer information.",
    "I am leaving plenty of room to revise that judgment.",
    "That is only a tentative read for me.",
    "I would need more concrete information before relying on that view.",
    "I am not confident enough to make that point decisive yet.",
    "I would keep this as an open question for now.",
    "There is still enough uncertainty that I would revisit it.",
    "I would rather verify that point before leaning on it heavily.",
    "That impression is still provisional for me.",
    "I would hold that view lightly until I know more.",
)

_HIGH_CONFIDENCE_CLOSERS = (
    "",
    "That factor carries meaningful weight in my decision.",
    "I feel fairly settled on that point at the moment.",
    "That is one of the clearer parts of my current view.",
    "I would need meaningful new evidence to move far from that position.",
    "That impression is relatively firm for me right now.",
    "I am giving that factor real weight in the overall decision.",
    "That point feels clearer to me than several of the other trade-offs.",
    "I am reasonably confident in that part of my assessment.",
    "That is a fairly stable part of my current judgment.",
    "I would still listen to new evidence, but I have a clear leaning there.",
    "That factor is unlikely to be neutral for me in the final decision.",
)


def _semantic_fallback(
    *,
    topic: str,
    stance: float,
    rng: object,
    confidence: float,
    style: SpeakingStyle,
    selector_key: str,
) -> str:
    """Compose deterministic, fact-bounded semantic wording.

    ``rng`` remains in the compatibility signature because callers historically
    supplied one, but wording selection is intentionally keyed only by
    ``selector_key`` so rendering never depends on mutable RNG order.
    """
    del rng
    band = stance_band(stance)
    topic_templates = _TOPIC_TEMPLATES.get(topic)
    core_choices = (
        topic_templates.get(band, _generic_templates(band))
        if topic_templates is not None
        else _generic_templates(band)
    )
    core = core_choices[_selector_index(selector_key, "core", len(core_choices))]
    # "review" is reserved by the language contract for external product-review
    # claims; use "check" when a template merely means inspecting product details.
    core = core.replace("review", "check")
    opener = _SEMANTIC_OPENERS[_selector_index(selector_key, "opener", len(_SEMANTIC_OPENERS))]

    if style.detail == "concise":
        closer = ""
    else:
        closer_pool = (
            _LOW_CONFIDENCE_CLOSERS
            if confidence < 0.40
            else _HIGH_CONFIDENCE_CLOSERS
            if confidence > 0.72
            else _MEASURED_CLOSERS
        )
        closer = closer_pool[_selector_index(selector_key, "closer", len(closer_pool))]

    composed = f"{opener}{core}"
    return f"{composed} {closer}" if closer else composed


def render_background_text(
    *,
    speaker: ConsumerAgent,
    listener: ConsumerAgent,
    topic: str,
    stance: float,
    conversation_id: str,
    dialogue_shape: DialogueShape = DialogueShape.uncertainty,
    speaking_style: SpeakingStyle | None = None,
    price_context: ConsumerPriceContext | None = None,
    decision_emphasis: bool = False,
    reply_to_topic: str | None = None,
    reply_to_stance: float | None = None,
) -> str:
    """Render deterministic wording after semantic stance is fixed.

    Traits affect expression through a compact speaking style; demographic labels are
    never used to infer price affordability or factual conclusions.
    """
    style = speaking_style or derive_speaking_style(AgentLanguageProfile.from_agent(speaker))
    band = stance_band(stance)
    if topic == "price":
        base = _price_text(
            band=band,
            price_context=price_context,
            conversation_id=conversation_id,
            speaker_id=speaker.agent_id,
            listener_id=listener.agent_id,
            shape=dialogue_shape,
        )
    else:
        base = _semantic_fallback(
            topic=topic,
            stance=stance,
            rng=None,
            confidence=speaker.state.confidence,
            style=style,
            selector_key=(
                f"{conversation_id}:{speaker.agent_id}:{listener.agent_id}:"
                f"{topic}:{dialogue_shape.value}"
            ),
        )

    reply_prefix = _reply_prefix(
        topic=topic,
        stance=stance,
        reply_to_topic=reply_to_topic,
        reply_to_stance=reply_to_stance,
        selector_key=conversation_id,
    )
    if reply_prefix:
        base = f"{reply_prefix} {base}"
    if _should_elaborate(style, conversation_id, speaker.agent_id, topic):
        base = f"{base} {_SHAPE_FOLLOW_UP[dialogue_shape]}"
    if decision_emphasis:
        decision = _purchase_decision_closer(speaker, conversation_id)
        if decision:
            base = f"{base} {decision}"
    return base


def _reply_prefix(
    *,
    topic: str,
    stance: float,
    reply_to_topic: str | None,
    reply_to_stance: float | None,
    selector_key: str,
) -> str:
    if reply_to_topic is None or reply_to_stance is None:
        return ""
    if topic == reply_to_topic:
        same_direction = stance * reply_to_stance > 0
        both_material = abs(stance) >= 0.12 and abs(reply_to_stance) >= 0.12
        if both_material and not same_direction:
            choices = _REPLY_DISAGREEMENT
        elif both_material and same_direction:
            choices = _REPLY_AGREEMENT
        else:
            return ""
        return choices[_selector_index(selector_key, "reply-prefix", len(choices))]

    if abs(reply_to_stance) >= 0.35:
        choices = _REPLY_TRANSITION
        return choices[_selector_index(selector_key, "reply-transition", len(choices))]
    return ""


_PASS_DECISIONS = (
    "As things stand, I would not buy it.",
    "At the moment, I would pass on this product.",
    "For now, I am not buying it.",
    "Given those concerns, I would walk away for now.",
)

_LEAN_PASS_DECISIONS = (
    "Overall, I am leaning toward not buying it.",
    "That leaves me more likely to pass than to buy right now.",
    "I would probably hold off rather than purchase it at this point.",
)

_CONSIDER_DECISIONS = (
    "Overall, I would seriously consider buying it.",
    "That leaves me fairly willing to consider a purchase.",
    "On balance, I would keep this on my shortlist to buy.",
)


def _purchase_decision_closer(speaker: ConsumerAgent, selector_key: str) -> str:
    purchase = speaker.state.purchase_intent
    opinion = speaker.state.overall_opinion
    if purchase <= 0.22 or (purchase <= 0.30 and opinion <= -0.20):
        choices = _PASS_DECISIONS
    elif purchase <= 0.40 and opinion < 0.0:
        choices = _LEAN_PASS_DECISIONS
    elif purchase >= 0.78 and opinion >= 0.20:
        choices = _CONSIDER_DECISIONS
    else:
        return ""
    return choices[_selector_index(selector_key, "purchase-decision", len(choices))]


def _price_text(
    *,
    band: str,
    price_context: ConsumerPriceContext | None,
    conversation_id: str,
    speaker_id: int,
    listener_id: int,
    shape: DialogueShape,
) -> str:
    if price_context is not None:
        # Price semantics are Python-owned. If a renderer stance and context ever
        # disagree, the explicit context wins for wording direction.
        band = _price_context_band(price_context)
        cadence = _cadence_label(price_context.billing_cadence)
    else:
        cadence = "price"
    choices = _PRICE_TEMPLATES[band]
    return choices[
        _stable_index(
            conversation_id,
            speaker_id,
            listener_id,
            f"price:{band}:{shape.value}",
            len(choices),
        )
    ].format(cadence=cadence)


def _price_context_band(context: ConsumerPriceContext) -> str:
    mapping = {
        "strongly_favorable": "strong_positive",
        "mildly_favorable": "mild_positive",
        "neutral_mixed": "neutral",
        "mildly_unfavorable": "moderate_negative" if context.stance <= -0.30 else "mild_negative",
        "strongly_unfavorable": "strong_negative",
    }
    return mapping[context.stance_band.value]


def _cadence_label(cadence: BillingCadence) -> str:
    return {
        BillingCadence.monthly: "monthly",
        BillingCadence.yearly: "yearly",
        BillingCadence.one_time: "one-time",
        BillingCadence.auto: "price",
    }[cadence]


def _generic_templates(band: str) -> tuple[str, ...]:
    if "negative" in band:
        return (
            "I have some real concerns about that part of the product.",
            "That aspect still makes me hesitate.",
            "I am leaning negative on that point for now.",
        )
    if "positive" in band:
        return (
            "I am leaning positive on that part of the product.",
            "That aspect works in the product's favor for me.",
            "I see that as a meaningful positive.",
        )
    return (
        "I am still undecided on that part.",
        "I can see both sides of that point.",
        "I do not have a strong view on that yet.",
    )


def _should_elaborate(
    style: SpeakingStyle,
    conversation_id: str,
    speaker_id: int,
    topic: str,
) -> bool:
    if style.detail == "concise":
        return False
    if style.detail == "elaborative":
        return True
    return bool(_stable_index(conversation_id, speaker_id, speaker_id, topic, 2))


def _selector_index(selector_key: str, salt: str, size: int) -> int:
    digest = hashlib.blake2b(
        f"{selector_key}:{salt}".encode("utf-8"),
        digest_size=4,
    ).digest()
    return int.from_bytes(digest, "big") % size


def _stable_index(
    conversation_id: str,
    speaker_id: int,
    listener_id: int,
    topic: str,
    size: int,
) -> int:
    digest = hashlib.blake2b(
        f"{conversation_id}:{speaker_id}:{listener_id}:{topic}".encode("utf-8"),
        digest_size=4,
    ).digest()
    return int.from_bytes(digest, "big") % size
