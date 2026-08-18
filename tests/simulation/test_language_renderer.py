import httpx
import pytest

from simulation.conversation.background_engine import generate_background_conversation
from simulation.conversation.language_renderer import render_conversation_language
from simulation.conversation.ledger import (
    AgentLanguageProfile,
    ConversationLanguageContext,
    ProductLanguageContext,
)
from simulation.conversation.models import ConversationPair
from simulation.llm.base import LLMJsonResponse, LLMUsage
from simulation.llm.deepseek import DeepSeekProvider
from simulation.llm.mock import MockLLMProvider
from simulation.network.knn_graph import build_knn_graph
from simulation.population.generator import generate_population
from simulation.product.pricing import (
    BillingCadence,
    ConsumerPriceContext,
    PricePosition,
    PriceStanceBand,
)


@pytest.mark.asyncio
async def test_deepseek_provider_returns_usage_cache_and_latency_telemetry():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/chat/completions"
        return httpx.Response(
            200,
            json={
                "model": "deepseek-v4-flash",
                "choices": [
                    {
                        "message": {
                            "content": '{"conversation":[{"speaker":"A","text":"Useful."},{"speaker":"B","text":"Price matters."}]}'
                        }
                    }
                ],
                "usage": {
                    "prompt_tokens": 120,
                    "prompt_cache_hit_tokens": 80,
                    "prompt_cache_miss_tokens": 40,
                    "completion_tokens": 20,
                    "total_tokens": 140,
                },
            },
        )

    provider = DeepSeekProvider(
        api_key="test-key",
        transport=httpx.MockTransport(handler),
    )

    response = await provider.generate_json(
        system_prompt="stable system",
        user_prompt="stable prefix then dynamic suffix",
        max_tokens=120,
    )

    assert response.data["conversation"][0]["speaker"] == "A"
    assert response.model == "deepseek-v4-flash"
    assert response.usage.prompt_tokens == 120
    assert response.usage.prompt_cache_hit_tokens == 80
    assert response.usage.prompt_cache_miss_tokens == 40
    assert response.usage.completion_tokens == 20
    assert response.usage.total_tokens == 140
    assert response.latency_ms >= 0


def test_conversation_language_context_refreshes_price_stance_from_current_agent_belief():
    agent_a, agent_b = generate_population(2, seed=92)
    agent_a.state.beliefs.price = -0.62
    agent_b.state.beliefs.price = 0.28
    base_context = ConsumerPriceContext(
        billing_cadence=BillingCadence.monthly,
        reference_price_inr=650.0,
        reference_ratio=500 / 650,
        position=PricePosition.typical,
        affordability=0.70,
        price_pressure=0.35,
        stance=0.35,
        stance_band=PriceStanceBand.mildly_favorable,
    )

    context = ConversationLanguageContext.from_agents(
        agent_a,
        agent_b,
        agent_a_price_context=base_context,
        agent_b_price_context=base_context,
    )

    assert context.agent_a_price_context is not None
    assert context.agent_b_price_context is not None
    assert context.agent_a_price_context.stance == pytest.approx(-0.62)
    assert context.agent_a_price_context.stance_band is PriceStanceBand.strongly_unfavorable
    assert context.agent_b_price_context.stance == pytest.approx(0.28)
    assert context.agent_b_price_context.stance_band is PriceStanceBand.mildly_favorable
    assert context.agent_a_price_context.affordability == base_context.affordability


def test_agent_language_profile_contains_full_consumer_context():
    agent = generate_population(2, seed=91)[0]

    profile = AgentLanguageProfile.from_agent(agent)

    assert profile.income_score == agent.income_score
    assert profile.price_sensitivity == agent.traits.price_sensitivity
    assert profile.technology_adoption == agent.traits.technology_adoption
    assert profile.product_need == agent.traits.product_need
    assert profile.risk_tolerance == agent.traits.risk_tolerance
    assert profile.brand_loyalty == agent.traits.brand_loyalty


@pytest.mark.asyncio
async def test_llm_renderer_changes_language_without_changing_semantic_messages():
    agents = generate_population(10, seed=14)
    graph = build_knn_graph(agents, k=3, seed=14)
    agent_a_id, agent_b_id = next(iter(graph.edges))
    pair = ConversationPair("language-test", 1, int(agent_a_id), int(agent_b_id), 0.8)
    snapshot = {agent.agent_id: agent for agent in agents}
    semantic = generate_background_conversation(pair, snapshot, graph, seed=17)
    original_messages = list(semantic.messages)
    language_context = ConversationLanguageContext.from_agents(
        snapshot[pair.agent_a_id], snapshot[pair.agent_b_id]
    )

    outcome = await render_conversation_language(
        pair=pair,
        semantic_result=semantic,
        language_context=language_context,
        provider=MockLLMProvider(),
        language_source="deepseek",
    )

    assert outcome.result.messages == original_messages
    assert outcome.result.language_source == "deepseek"
    assert len(outcome.result.transcript) == 2
    assert outcome.result.transcript[0]["speaker_id"] == pair.agent_a_id
    assert outcome.result.transcript[1]["speaker_id"] == pair.agent_b_id
    assert all(message["text"] for message in outcome.result.transcript)
    assert outcome.succeeded is True
    assert outcome.provider_response is not None
    assert outcome.provider_response.model == "mock"


class CapturingProvider:
    def __init__(self):
        self.user_prompt = ""
        self.user_prompts: list[str] = []
        self.system_prompt = ""
        self.max_tokens = None
        self.json_schema = None

    async def generate_json(
        self,
        *,
        system_prompt,
        user_prompt,
        max_tokens=700,
        json_schema=None,
    ):
        self.user_prompt = user_prompt
        self.user_prompts.append(user_prompt)
        self.system_prompt = system_prompt
        self.max_tokens = max_tokens
        self.json_schema = json_schema
        return LLMJsonResponse(
            data={
                "conversation": [
                    {"speaker": "A", "text": "The personalized plan sounds useful."},
                    {"speaker": "B", "text": "I would still compare the monthly price."},
                ]
            },
            usage=LLMUsage(
                prompt_tokens=100,
                prompt_cache_hit_tokens=60,
                prompt_cache_miss_tokens=40,
                completion_tokens=20,
                total_tokens=120,
            ),
            latency_ms=25.0,
            model="capture-model",
        )


@pytest.mark.asyncio
async def test_llm_renderer_receives_bounded_product_context():
    agents = generate_population(10, seed=31)
    graph = build_knn_graph(agents, k=3, seed=31)
    agent_a_id, agent_b_id = next(iter(graph.edges))
    pair = ConversationPair("product-context", 1, int(agent_a_id), int(agent_b_id), 0.8)
    snapshot = {agent.agent_id: agent for agent in agents}
    semantic = generate_background_conversation(pair, snapshot, graph, seed=32)
    provider = CapturingProvider()

    await render_conversation_language(
        pair=pair,
        semantic_result=semantic,
        language_context=ConversationLanguageContext.from_agents(
            snapshot[pair.agent_a_id], snapshot[pair.agent_b_id]
        ),
        product_context=ProductLanguageContext(
            name="AI Fitness Coach",
            category="Fitness Technology",
            price=999,
            currency="INR",
            pitch_excerpt="Personalized workouts and nutrition guidance.",
        ),
        provider=provider,
        language_source="deepseek",
    )

    assert '"name":"AI Fitness Coach"' in provider.user_prompt
    assert '"price":999' in provider.user_prompt
    assert '"income_score":' not in provider.user_prompt
    assert '"price_sensitivity":' not in provider.user_prompt
    assert '"technology_adoption":' not in provider.user_prompt
    assert '"product_need":' not in provider.user_prompt
    assert '"risk_tolerance":' not in provider.user_prompt
    assert '"brand_loyalty":' not in provider.user_prompt
    assert '"overall_opinion":' not in provider.user_prompt
    assert '"argument_strength":' not in provider.user_prompt
    assert '"price_pressure":' not in provider.user_prompt
    assert '"affordability":' not in provider.user_prompt
    assert '"argument_band":' in provider.user_prompt
    assert '"knowledge_band":' in provider.user_prompt
    assert provider.json_schema["properties"]["conversation"]["minItems"] == len(semantic.messages)
    assert provider.json_schema["properties"]["conversation"]["maxItems"] == len(semantic.messages)
    assert len(provider.user_prompt) < 5000


@pytest.mark.asyncio
async def test_llm_renderer_receives_price_context_style_shape_and_anti_bias_contract():
    agents = generate_population(10, seed=36)
    graph = build_knn_graph(agents, k=3, seed=36)
    agent_a_id, agent_b_id = next(iter(graph.edges))
    pair = ConversationPair("realism-contract", 1, int(agent_a_id), int(agent_b_id), 0.8)
    snapshot = {agent.agent_id: agent for agent in agents}
    semantic = generate_background_conversation(pair, snapshot, graph, seed=37)
    provider = CapturingProvider()
    favorable = ConsumerPriceContext(
        billing_cadence=BillingCadence.monthly,
        reference_price_inr=650.0,
        reference_ratio=200 / 650,
        position=PricePosition.inexpensive,
        affordability=0.82,
        price_pressure=0.14,
        stance=0.58,
        stance_band=PriceStanceBand.strongly_favorable,
    )
    mixed = ConsumerPriceContext(
        billing_cadence=BillingCadence.monthly,
        reference_price_inr=650.0,
        reference_ratio=500 / 650,
        position=PricePosition.typical,
        affordability=0.58,
        price_pressure=0.44,
        stance=0.08,
        stance_band=PriceStanceBand.neutral_mixed,
    )

    await render_conversation_language(
        pair=pair,
        semantic_result=semantic,
        language_context=ConversationLanguageContext.from_agents(
            snapshot[pair.agent_a_id],
            snapshot[pair.agent_b_id],
            agent_a_price_context=favorable,
            agent_b_price_context=mixed,
        ),
        product_context=ProductLanguageContext(
            name="AI Fitness Coach",
            category="Fitness Technology",
            price=200,
            currency="INR",
            pitch_excerpt="Personalized workouts and nutrition guidance.",
            billing_cadence=BillingCadence.monthly,
        ),
        provider=provider,
        language_source="deepseek",
    )

    system = provider.system_prompt.lower()
    assert "do not infer" in system
    assert "occupation" in system
    assert "age" in system
    assert "student" in system
    assert "afford" in system
    assert "free alternative" in system
    assert "competitor" in system
    assert "gym" in system
    assert "market average" in system
    assert "review" in system
    assert "1-2 sentences" in system
    assert "up to 3 sentences" in system
    assert "filler" in system
    assert '"dialogue_shape":' in provider.user_prompt
    assert '"consumer":' in provider.user_prompt
    assert '"price_context":' in provider.user_prompt
    assert '"stance_band":' in provider.user_prompt
    assert '"billing_cadence":"monthly"' in provider.user_prompt
    assert "A|B" not in provider.user_prompt
    assert "A|B" not in provider.system_prompt
    assert provider.max_tokens == 600
    assert provider.json_schema["properties"]["conversation"]["items"]["properties"]["text"]["maxLength"] == 900


@pytest.mark.asyncio
async def test_llm_renderer_places_stable_contract_and_product_before_dynamic_context():
    agents = generate_population(10, seed=41)
    graph = build_knn_graph(agents, k=3, seed=41)
    edges = list(graph.edges)[:2]
    provider = CapturingProvider()
    product = ProductLanguageContext(
        name="AI Fitness Coach",
        category="Fitness Technology",
        price=999,
        currency="INR",
        pitch_excerpt="Personalized workouts and nutrition guidance.",
    )
    snapshot = {agent.agent_id: agent for agent in agents}

    for index, (agent_a_id, agent_b_id) in enumerate(edges, start=1):
        pair = ConversationPair(
            f"cache-prefix-{index}",
            1,
            int(agent_a_id),
            int(agent_b_id),
            0.8,
        )
        semantic = generate_background_conversation(pair, snapshot, graph, seed=50 + index)
        await render_conversation_language(
            pair=pair,
            semantic_result=semantic,
            language_context=ConversationLanguageContext.from_agents(
                snapshot[pair.agent_a_id], snapshot[pair.agent_b_id]
            ),
            product_context=product,
            provider=provider,
            language_source="deepseek",
        )

    assert len(provider.user_prompts) == 2
    prefix_a = provider.user_prompts[0].split('"dynamic_conversation":', 1)[0]
    prefix_b = provider.user_prompts[1].split('"dynamic_conversation":', 1)[0]
    assert prefix_a == prefix_b
    assert '"renderer_contract"' in prefix_a
    assert '"product"' in prefix_a
    assert '"conversation_id"' not in prefix_a
    assert provider.user_prompts[0].index('"renderer_contract"') < provider.user_prompts[0].index('"product"')
    assert provider.user_prompts[0].index('"product"') < provider.user_prompts[0].index('"dynamic_conversation"')


class SemanticContractViolatingProvider:
    async def generate_json(self, **_kwargs):
        return LLMJsonResponse(
            data={
                "conversation": [
                    {"speaker": "A", "text": "My income score is 0.56, so this looks affordable."},
                    {"speaker": "B", "text": "Have you checked the reviews on that?"},
                ]
            },
            usage=LLMUsage(
                prompt_tokens=90,
                prompt_cache_hit_tokens=0,
                prompt_cache_miss_tokens=90,
                completion_tokens=20,
                total_tokens=110,
            ),
            latency_ms=12.0,
            model="test-model",
        )


@pytest.mark.asyncio
async def test_schema_valid_but_semantically_invalid_live_response_falls_back_with_issue_codes():
    from simulation.audit.logger import MemoryRunAuditLogger

    agents = generate_population(10, seed=58)
    graph = build_knn_graph(agents, k=3, seed=58)
    agent_a_id, agent_b_id = next(iter(graph.edges))
    pair = ConversationPair("semantic-contract-fallback", 1, int(agent_a_id), int(agent_b_id), 0.8)
    snapshot = {agent.agent_id: agent for agent in agents}
    semantic = generate_background_conversation(pair, snapshot, graph, seed=59)
    audit = MemoryRunAuditLogger(run_id="semantic-validation")

    outcome = await render_conversation_language(
        pair=pair,
        semantic_result=semantic,
        language_context=ConversationLanguageContext.from_agents(
            snapshot[pair.agent_a_id], snapshot[pair.agent_b_id]
        ),
        provider=SemanticContractViolatingProvider(),
        language_source="deepseek",
        audit=audit,
    )

    assert outcome.succeeded is False
    assert outcome.result.transcript == semantic.transcript
    failure = next(event for event in audit.events if event["event"] == "language.render.validation_failed")
    assert set(failure["payload"]["issue_codes"]) >= {
        "internal_state_leak",
        "unsupported_external_fact",
    }
    fallback = next(event for event in audit.events if event["event"] == "language.render.fallback")
    assert fallback["payload"]["stage"] == "semantic_contract"


class MalformedTelemetryProvider:
    async def generate_json(self, **_kwargs):
        return LLMJsonResponse(
            data={"unexpected": True},
            usage=LLMUsage(
                prompt_tokens=90,
                prompt_cache_hit_tokens=50,
                prompt_cache_miss_tokens=40,
                completion_tokens=5,
                total_tokens=95,
            ),
            latency_ms=18.0,
            model="deepseek-v4-flash",
        )


@pytest.mark.asyncio
async def test_llm_renderer_keeps_billable_telemetry_when_output_validation_falls_back():
    agents = generate_population(10, seed=61)
    graph = build_knn_graph(agents, k=3, seed=61)
    agent_a_id, agent_b_id = next(iter(graph.edges))
    pair = ConversationPair("billable-fallback", 1, int(agent_a_id), int(agent_b_id), 0.8)
    snapshot = {agent.agent_id: agent for agent in agents}
    semantic = generate_background_conversation(pair, snapshot, graph, seed=62)

    outcome = await render_conversation_language(
        pair=pair,
        semantic_result=semantic,
        language_context=ConversationLanguageContext.from_agents(
            snapshot[pair.agent_a_id], snapshot[pair.agent_b_id]
        ),
        provider=MalformedTelemetryProvider(),
        language_source="deepseek",
    )

    assert outcome.succeeded is False
    assert outcome.result.language_source == "background"
    assert outcome.provider_response is not None
    assert outcome.provider_response.usage.total_tokens == 95


class BrokenProvider:
    async def generate_json(self, **_kwargs):
        return {"unexpected": True}


@pytest.mark.asyncio
async def test_llm_renderer_falls_back_to_existing_background_transcript():
    agents = generate_population(10, seed=21)
    graph = build_knn_graph(agents, k=3, seed=21)
    agent_a_id, agent_b_id = next(iter(graph.edges))
    pair = ConversationPair("fallback-test", 1, int(agent_a_id), int(agent_b_id), 0.8)
    snapshot = {agent.agent_id: agent for agent in agents}
    semantic = generate_background_conversation(pair, snapshot, graph, seed=22)
    language_context = ConversationLanguageContext.from_agents(
        snapshot[pair.agent_a_id], snapshot[pair.agent_b_id]
    )

    outcome = await render_conversation_language(
        pair=pair,
        semantic_result=semantic,
        language_context=language_context,
        provider=BrokenProvider(),
        language_source="deepseek",
    )

    assert outcome.result.messages == semantic.messages
    assert outcome.result.transcript == semantic.transcript
    assert outcome.result.language_source == "background"
    assert outcome.succeeded is False
    assert outcome.provider_response is None
