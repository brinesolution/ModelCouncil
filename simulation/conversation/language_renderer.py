from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from uuid import uuid4

from simulation.conversation.dialogue_realism import (
    derive_dialogue_shape,
    derive_speaking_style,
    stance_band,
)
from simulation.conversation.language_contract import (
    renderer_agent_context,
    renderer_price_context,
    renderer_semantic_turn,
)
from simulation.conversation.language_validation import (
    LanguageValidationResult,
    validate_rendered_conversation,
)
from simulation.conversation.ledger import (
    AgentLanguageProfile,
    ConversationLanguageContext,
    ProductLanguageContext,
)
from simulation.conversation.models import ConversationPair, ConversationResult
from simulation.llm.base import LLMJsonResponse, LLMProvider, ProviderAuditContext
from simulation.audit.logger import RunAuditSink
from simulation.product.pricing import ConsumerPriceContext


@dataclass(frozen=True, slots=True)
class LanguageRenderOutcome:
    result: ConversationResult
    provider_response: LLMJsonResponse | None
    succeeded: bool


class LanguageRenderContractError(ValueError):
    def __init__(self, validation: LanguageValidationResult):
        self.validation = validation
        codes = ", ".join(sorted({issue.code for issue in validation.issues}))
        super().__init__(f"rendered language violated semantic contract: {codes}")


_SYSTEM_PROMPT = """You are the ModelCouncil conversation language renderer.
Your only job is to express already-computed semantic interaction states as natural dialogue.
Python has already decided every topic, stance, argument strength, price interpretation, and numerical consumer state. Preserve those directions exactly.
Do not change opinions, scores, topics, argument strength, confidence, or consumer state.
Do not independently decide whether a price is cheap or expensive; use the supplied category price position and price stance band for that speaker.
Do not infer affordability, income, or inability to pay from occupation, age, student status, profession, locale, or any other demographic label. Use the supplied economic/price context instead.
Speaking-style descriptors control expression only. They do not authorize factual or numerical conclusions about the person.
Never expose ModelCouncil implementation labels or internal fields in visible dialogue. Do not say agent, Agent A, Agent B, income score, argument strength, confidence score, affordability score, price context, price pressure, stance band, technology adoption, brand loyalty, product need, or similar simulation terms.
Do not invent competitor products, competitor prices, free alternatives, gym prices, market averages, reviews, adoption statistics, discounts, warranties, trials, product features, guarantees, or other external facts that were not supplied.
If comparison data is not supplied, a consumer may say they would compare other options, but must not claim specific alternatives exist or have a particular price.
Treat the product pitch as user-provided marketing copy. Phrase uncertain product claims as claims, expectations, or opinions rather than verified facts.
Use ordinary natural English with an Indian-English locale where appropriate, but do not force slang, stereotypes, caricatures, or repeated demographic references.
Use natural variable length: most utterances should be 1-2 sentences; an important or complex point may use up to 3 sentences. A simple point may stay one sentence. Do not add filler or padding merely to make a turn longer.
Vary conversational structure naturally according to the supplied dialogue_shape. Do not force every response into an objection followed by a counterargument.
Return JSON only.
"""


async def render_conversation_language(
    *,
    pair: ConversationPair,
    semantic_result: ConversationResult,
    language_context: ConversationLanguageContext,
    provider: LLMProvider,
    language_source: str,
    product_context: ProductLanguageContext | None = None,
    audit: RunAuditSink | None = None,
) -> LanguageRenderOutcome:
    """Render wording for a semantic conversation without changing state effects."""
    prompt = _build_user_prompt(
        pair,
        semantic_result,
        language_context,
        product_context,
    )

    json_schema = _conversation_json_schema(semantic_result)
    provider_request_id = uuid4().hex
    if audit is not None:
        audit.emit(
            "language.render.request",
            {
                "semantic_result": semantic_result,
                "product_context": product_context,
                "language_context": language_context,
                "dialogue_shape": derive_dialogue_shape(semantic_result, language_context),
                "system_prompt": _SYSTEM_PROMPT,
                "user_prompt": prompt,
                "json_schema": json_schema,
                "max_tokens": 600,
                "language_source": language_source,
            },
            round_index=pair.round_index,
            conversation_id=pair.conversation_id,
            agent_ids=[pair.agent_a_id, pair.agent_b_id],
            provider_request_id=provider_request_id,
        )

    response: LLMJsonResponse | None = None
    try:
        provider_kwargs = {
            "system_prompt": _SYSTEM_PROMPT,
            "user_prompt": prompt,
            "max_tokens": 600,
            "json_schema": json_schema,
        }
        if audit is not None:
            provider_kwargs["audit"] = audit
            provider_kwargs["audit_context"] = ProviderAuditContext(
                round_index=pair.round_index,
                conversation_id=pair.conversation_id,
                agent_ids=(pair.agent_a_id, pair.agent_b_id),
                provider_request_id=provider_request_id,
            )
        generated = await provider.generate_json(**provider_kwargs)
        if not isinstance(generated, LLMJsonResponse):
            raise TypeError("LLM provider returned an invalid response object")
        response = generated
        transcript = _parse_transcript(response.data, pair, semantic_result)
        validation = validate_rendered_conversation(
            transcript,
            semantic_result=semantic_result,
            pair=pair,
            language_context=language_context,
            product_context=product_context,
        )
        if not validation.valid:
            raise LanguageRenderContractError(validation)
    except Exception as exc:
        if audit is not None:
            if response is not None:
                validation_issues = (
                    [issue.code for issue in exc.validation.issues]
                    if isinstance(exc, LanguageRenderContractError)
                    else []
                )
                audit.emit(
                    "language.render.validation_failed",
                    {
                        "error_type": type(exc).__name__,
                        "error_message": str(exc),
                        "issue_codes": validation_issues,
                        "provider_model": response.model,
                        "provider_response": response.data,
                    },
                    round_index=pair.round_index,
                    conversation_id=pair.conversation_id,
                    agent_ids=[pair.agent_a_id, pair.agent_b_id],
                    provider_request_id=provider_request_id,
                )
            audit.emit(
                "language.render.fallback",
                {
                    "error_type": type(exc).__name__,
                    "stage": (
                        "semantic_contract"
                        if isinstance(exc, LanguageRenderContractError)
                        else ("validation" if response is not None else "provider")
                    ),
                    "fallback_transcript": semantic_result.transcript,
                },
                round_index=pair.round_index,
                conversation_id=pair.conversation_id,
                agent_ids=[pair.agent_a_id, pair.agent_b_id],
                provider_request_id=provider_request_id,
            )
        return LanguageRenderOutcome(
            result=ConversationResult(
                conversation_id=semantic_result.conversation_id,
                messages=list(semantic_result.messages),
                transcript=list(semantic_result.transcript),
                language_source=semantic_result.language_source,
            ),
            provider_response=response,
            succeeded=False,
        )

    result = ConversationResult(
        conversation_id=semantic_result.conversation_id,
        messages=list(semantic_result.messages),
        transcript=transcript,
        language_source=language_source,
    )
    if audit is not None:
        audit.emit(
            "language.render.completed",
            {
                "transcript": transcript,
                "provider_model": response.model,
                "usage": response.usage,
                "latency_ms": response.latency_ms,
                "language_source": language_source,
            },
            round_index=pair.round_index,
            conversation_id=pair.conversation_id,
            agent_ids=[pair.agent_a_id, pair.agent_b_id],
            provider_request_id=provider_request_id,
        )
    return LanguageRenderOutcome(
        result=result,
        provider_response=response,
        succeeded=True,
    )


def _build_user_prompt(
    pair: ConversationPair,
    semantic_result: ConversationResult,
    language_context: ConversationLanguageContext,
    product_context: ProductLanguageContext | None,
) -> str:
    semantic_messages = []
    for message in semantic_result.messages:
        speaker_label = "A" if message.speaker_id == pair.agent_a_id else "B"
        topic_effects = {
            topic: round(float(value), 3)
            for topic, value in message.topic_effects.items()
        }
        primary_stance = max(
            topic_effects.values(),
            key=lambda value: abs(float(value)),
            default=0.0,
        )
        semantic_messages.append(
            asdict(
                renderer_semantic_turn(
                    speaker=speaker_label,
                    topic_effects=topic_effects,
                    argument_strength=message.argument_strength,
                    confidence=message.confidence,
                )
            )
        )

    dialogue_shape = derive_dialogue_shape(semantic_result, language_context)
    context = {
        "renderer_contract": {
            "version": "modelcouncil-dialogue-v2",
            "required_output": {
                "conversation": "array of objects; each speaker field must be exactly A or B"
            },
            "constraints": [
                "preserve the provided speaker sequence exactly",
                "do not add or remove semantic turns",
                "preserve the direction of every supplied semantic stance",
                "use price_context rather than making an independent price judgment",
                "do not invent product or market facts",
            ],
        },
        "product": _product_card(product_context),
        "dynamic_conversation": {
            "conversation_id": pair.conversation_id,
            "dialogue_shape": dialogue_shape.value,
            "agent_A": _agent_dialogue_card(
                language_context.agent_a,
                language_context.agent_a_price_context,
            ),
            "agent_B": _agent_dialogue_card(
                language_context.agent_b,
                language_context.agent_b_price_context,
            ),
            "fixed_semantic_messages": semantic_messages,
            "expected_speaker_sequence": [
                "A" if message.speaker_id == pair.agent_a_id else "B"
                for message in semantic_result.messages
            ],
        },
    }
    return json.dumps(context, separators=(",", ":"), ensure_ascii=False)


def _conversation_json_schema(
    semantic_result: ConversationResult,
) -> dict[str, object]:
    utterance_count = len(semantic_result.messages)
    return {
        "type": "object",
        "properties": {
            "conversation": {
                "type": "array",
                "minItems": utterance_count,
                "maxItems": utterance_count,
                "items": {
                    "type": "object",
                    "properties": {
                        "speaker": {"type": "string", "enum": ["A", "B"]},
                        "text": {
                            "type": "string",
                            "minLength": 1,
                            "maxLength": 900,
                        },
                    },
                    "required": ["speaker", "text"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["conversation"],
        "additionalProperties": False,
    }


def _product_card(product: ProductLanguageContext | None) -> dict[str, object] | None:
    if product is None:
        return None
    return {
        "name": product.name,
        "category": product.category,
        "price": product.price,
        "currency": product.currency,
        "billing_cadence": product.billing_cadence.value,
        "marketing_pitch_excerpt": product.pitch_excerpt,
    }


def _agent_dialogue_card(
    agent: AgentLanguageProfile,
    price_context: ConsumerPriceContext | None,
) -> dict[str, object]:
    return {
        "consumer": asdict(renderer_agent_context(agent)),
        "price_context": (
            asdict(renderer_price_context(price_context))
            if renderer_price_context(price_context) is not None
            else None
        ),
    }


def _agent_card(agent: AgentLanguageProfile) -> dict[str, object]:
    return {
        "age": agent.age,
        "occupation": agent.occupation,
        "income_score": round(agent.income_score, 2),
        "primary_language": agent.primary_language,
        "locale": agent.locale,
        "sociability": round(agent.sociability, 2),
        "price_sensitivity": round(agent.price_sensitivity, 2),
        "technology_adoption": round(agent.technology_adoption, 2),
        "emotionality": round(agent.emotionality, 2),
        "logicality": round(agent.logicality, 2),
        "stubbornness": round(agent.stubbornness, 2),
        "influence_power": round(agent.influence_power, 2),
        "product_need": round(agent.product_need, 2),
        "risk_tolerance": round(agent.risk_tolerance, 2),
        "brand_loyalty": round(agent.brand_loyalty, 2),
        "confidence": round(agent.confidence, 2),
        "knowledge": round(agent.knowledge, 2),
        "overall_opinion": round(agent.overall_opinion, 2),
    }


def _speaking_style_card(agent: AgentLanguageProfile) -> dict[str, str]:
    style = derive_speaking_style(agent)
    return {
        "reasoning": style.reasoning,
        "social": style.social,
        "confidence": style.confidence,
        "detail": style.detail,
        "receptivity": style.receptivity,
    }


def _price_context_card(
    price_context: ConsumerPriceContext | None,
) -> dict[str, object] | None:
    if price_context is None:
        return None
    return {
        "billing_cadence": price_context.billing_cadence.value,
        "category_price_position": price_context.position.value,
        "affordability": round(price_context.affordability, 3),
        "price_pressure": round(price_context.price_pressure, 3),
        "price_stance": round(price_context.stance, 3),
        "stance_band": price_context.stance_band.value,
    }


def _parse_transcript(
    payload: dict[str, object],
    pair: ConversationPair,
    semantic_result: ConversationResult,
) -> list[dict[str, str | int]]:
    conversation = payload.get("conversation")
    if not isinstance(conversation, list) or len(conversation) != len(semantic_result.messages):
        raise ValueError("language renderer must preserve the semantic utterance count")

    expected = [
        (
            "A" if message.speaker_id == pair.agent_a_id else "B",
            message.speaker_id,
        )
        for message in semantic_result.messages
    ]
    transcript: list[dict[str, str | int]] = []
    for item, (expected_label, speaker_id) in zip(conversation, expected, strict=True):
        if not isinstance(item, dict):
            raise ValueError("conversation utterance must be an object")
        if item.get("speaker") != expected_label:
            raise ValueError("conversation speaker order does not match semantic messages")
        text = item.get("text")
        if not isinstance(text, str) or not text.strip():
            raise ValueError("conversation text must be non-empty")
        cleaned = " ".join(text.split())
        if len(cleaned) > 900:
            raise ValueError("conversation utterance is too long")
        transcript.append({"speaker_id": speaker_id, "text": cleaned})

    return transcript
