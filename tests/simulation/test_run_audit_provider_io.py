import json

import httpx
import pytest

from simulation.audit.logger import MemoryRunAuditLogger
from simulation.conversation.background_engine import generate_background_conversation
from simulation.conversation.language_renderer import render_conversation_language
from simulation.conversation.ledger import ConversationLanguageContext, ProductLanguageContext
from simulation.conversation.models import ConversationPair
from simulation.llm.base import LLMJsonResponse, LLMUsage, ProviderAuditContext
from simulation.llm.deepseek import DeepSeekProvider
from simulation.llm.ollama import OllamaProvider
from simulation.network.knn_graph import build_knn_graph
from simulation.population.generator import generate_population


@pytest.mark.asyncio
async def test_deepseek_audit_records_safe_exact_request_and_visible_response_without_secret_or_private_reasoning():
    secret = "test-live-secret-123"

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert request.headers["Authorization"] == f"Bearer {secret}"
        return httpx.Response(
            200,
            json={
                "model": "deepseek-v4-flash",
                "choices": [
                    {
                        "message": {
                            "content": '{"conversation":[{"speaker":"A","text":"Useful."},{"speaker":"B","text":"Fair."}]}',
                            "reasoning_content": "private reasoning must never persist",
                        }
                    }
                ],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
                "metadata": {"notice": f"provider echoed credential {secret}"},
            },
        )

    audit = MemoryRunAuditLogger(run_id="deepseek")
    provider = DeepSeekProvider(api_key=secret, transport=httpx.MockTransport(handler))
    context = ProviderAuditContext(
        round_index=2,
        conversation_id="r2-a1-a2",
        agent_ids=(1, 2),
        provider_request_id="provider-1",
    )

    response = await provider.generate_json(
        system_prompt="system",
        user_prompt="user",
        max_tokens=123,
        audit=audit,
        audit_context=context,
    )

    requests = [event for event in audit.events if event["event"] == "provider.http.request"]
    responses = [event for event in audit.events if event["event"] == "provider.http.response"]
    assert len(requests) == len(responses) == 1
    request_payload = requests[0]["payload"]
    assert request_payload["method"] == "POST"
    assert request_payload["endpoint"].endswith("/chat/completions")
    assert request_payload["headers"]["Authorization"] == "[REDACTED]"
    assert request_payload["json"]["max_tokens"] == 123
    assert responses[0]["payload"]["status_code"] == 200
    assert responses[0]["payload"]["parsed_assistant_json"] == response.data
    serialized = json.dumps(audit.events)
    assert secret not in serialized
    assert "private reasoning must never persist" not in serialized
    assert "[OMITTED_PRIVATE_REASONING]" in serialized


@pytest.mark.asyncio
async def test_ollama_audit_records_schema_options_and_visible_response():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "model": "qwen3:0.6b",
                "message": {
                    "role": "assistant",
                    "content": '{"conversation":[]}',
                    "thinking": "ollama private reasoning must never persist",
                },
                "prompt_eval_count": 44,
                "eval_count": 7,
            },
        )

    audit = MemoryRunAuditLogger(run_id="ollama")
    provider = OllamaProvider(
        model="qwen3:0.6b",
        context_window=2048,
        transport=httpx.MockTransport(handler),
    )
    schema = {"type": "object", "properties": {"conversation": {"type": "array"}}}

    await provider.generate_json(
        system_prompt="system",
        user_prompt="user",
        max_tokens=321,
        json_schema=schema,
        audit=audit,
        audit_context=ProviderAuditContext(provider_request_id="ollama-1"),
    )

    assert captured["format"] == schema
    assert captured["options"]["num_ctx"] == 2048
    assert captured["options"]["num_predict"] == 321
    request = next(event for event in audit.events if event["event"] == "provider.http.request")
    response = next(event for event in audit.events if event["event"] == "provider.http.response")
    assert request["payload"]["json"]["format"] == schema
    assert response["payload"]["body"]["prompt_eval_count"] == 44
    assert response["payload"]["body"]["eval_count"] == 7
    assert response["payload"]["body"]["message"]["thinking"] == "[OMITTED_PRIVATE_REASONING]"
    assert "ollama private reasoning must never persist" not in json.dumps(audit.events)


class InvalidTranscriptProvider:
    async def generate_json(self, **_kwargs):
        return LLMJsonResponse(
            data={"conversation": [{"speaker": "B", "text": "Wrong order"}]},
            usage=LLMUsage(total_tokens=5),
            latency_ms=1.0,
            model="invalid",
        )


@pytest.mark.asyncio
async def test_language_renderer_audits_full_render_contract_and_fallback_validation():
    agents = generate_population(10, seed=73)
    graph = build_knn_graph(agents, k=3, seed=73)
    a, b = next(iter(graph.edges))
    pair = ConversationPair("r1-a%d-a%d" % (a, b), 1, int(a), int(b), 0.8)
    snapshot = {agent.agent_id: agent for agent in agents}
    semantic = generate_background_conversation(pair, snapshot, graph, seed=74)
    context = ConversationLanguageContext.from_agents(snapshot[int(a)], snapshot[int(b)])
    product = ProductLanguageContext(
        name="Coach",
        category="Fitness Technology",
        price=500,
        currency="INR",
        pitch_excerpt="Personalized coaching.",
    )
    audit = MemoryRunAuditLogger(run_id="renderer")

    outcome = await render_conversation_language(
        pair=pair,
        semantic_result=semantic,
        language_context=context,
        product_context=product,
        provider=InvalidTranscriptProvider(),
        language_source="deepseek",
        audit=audit,
    )

    request = next(event for event in audit.events if event["event"] == "language.render.request")
    assert request["payload"]["system_prompt"]
    assert request["payload"]["user_prompt"]
    assert request["payload"]["json_schema"]["properties"]["conversation"]
    assert request["payload"]["semantic_result"]["conversation_id"] == pair.conversation_id
    assert any(event["event"] == "language.render.validation_failed" for event in audit.events)
    assert any(event["event"] == "language.render.fallback" for event in audit.events)
    assert outcome.succeeded is False
    assert outcome.result.transcript == semantic.transcript
