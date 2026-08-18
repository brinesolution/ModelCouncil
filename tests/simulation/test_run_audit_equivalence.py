import json

import httpx
import pytest

from backend.app.services.run_audit_service import emit_run_failed, finalize_run_audit
from simulation.audit.logger import JsonlRunAuditLogger, MemoryRunAuditLogger, NullRunAuditLogger
from simulation.engine import SimulationConfig, SimulationEngine
from simulation.llm.base import ProviderAuditContext
from simulation.llm.deepseek import DeepSeekProvider
from simulation.llm.ollama import OllamaProvider
from simulation.population.generator import generate_population
from simulation.product.knowledge import ProductKnowledge


def _product() -> ProductKnowledge:
    return ProductKnowledge(
        name="Audit Equivalence Coach",
        category="Fitness Technology",
        pitch="Personalized coaching and progress tracking for a monthly subscription.",
        price=500,
        currency="INR",
        billing_cadence="monthly",
    )


def _result_signature(result):
    return {
        "timeline": result.timeline,
        "population": result.population,
        "conversations": [
            (entry.pair, entry.result, entry.trust, entry.relationship_strength, entry.similarity, entry.weak_tie)
            for entry in result.conversations
        ],
        "checkpoints": result.checkpoints,
        "nodes": sorted((int(node), dict(data)) for node, data in result.graph.nodes(data=True)),
        "edges": sorted(
            (min(int(a), int(b)), max(int(a), int(b)), dict(data))
            for a, b, data in result.graph.edges(data=True)
        ),
    }


def test_null_memory_and_jsonl_audit_produce_identical_simulation_outputs(tmp_path):
    population = generate_population(50, seed=202)
    config = SimulationConfig(rounds=4, seed=202, k=6, initiator_rate=0.3)

    null_result = SimulationEngine().run(_product(), population, config, audit=NullRunAuditLogger())
    memory_result = SimulationEngine().run(
        _product(), population, config, audit=MemoryRunAuditLogger(run_id="memory")
    )
    jsonl = JsonlRunAuditLogger(root=tmp_path, run_id="jsonl")
    jsonl_result = SimulationEngine().run(_product(), population, config, audit=jsonl)
    jsonl.close()

    expected = _result_signature(null_result)
    assert _result_signature(memory_result) == expected
    assert _result_signature(jsonl_result) == expected


@pytest.mark.asyncio
async def test_deepseek_and_ollama_request_payloads_are_identical_with_audit_on_or_off():
    deepseek_requests = []

    def deepseek_handler(request: httpx.Request) -> httpx.Response:
        deepseek_requests.append(
            {
                "url": str(request.url),
                "authorization": request.headers.get("Authorization"),
                "json": json.loads(request.content),
            }
        )
        return httpx.Response(
            200,
            json={
                "model": "deepseek-v4-flash",
                "choices": [{"message": {"content": '{"conversation":[]}'}}],
                "usage": {},
            },
        )

    provider = DeepSeekProvider(
        api_key="equivalence-secret",
        transport=httpx.MockTransport(deepseek_handler),
    )
    kwargs = dict(system_prompt="system", user_prompt="user", max_tokens=111)
    await provider.generate_json(**kwargs)
    await provider.generate_json(
        **kwargs,
        audit=MemoryRunAuditLogger(run_id="deepseek-audit"),
        audit_context=ProviderAuditContext(provider_request_id="d1"),
    )
    assert deepseek_requests[0] == deepseek_requests[1]

    ollama_requests = []

    def ollama_handler(request: httpx.Request) -> httpx.Response:
        ollama_requests.append({"url": str(request.url), "json": json.loads(request.content)})
        return httpx.Response(
            200,
            json={
                "model": "qwen3:0.6b",
                "message": {"content": '{"conversation":[]}'},
                "prompt_eval_count": 1,
                "eval_count": 1,
            },
        )

    ollama = OllamaProvider(
        model="qwen3:0.6b",
        transport=httpx.MockTransport(ollama_handler),
    )
    schema = {"type": "object", "properties": {"conversation": {"type": "array"}}}
    ollama_kwargs = dict(system_prompt="system", user_prompt="user", max_tokens=222, json_schema=schema)
    await ollama.generate_json(**ollama_kwargs)
    await ollama.generate_json(
        **ollama_kwargs,
        audit=MemoryRunAuditLogger(run_id="ollama-audit"),
        audit_context=ProviderAuditContext(provider_request_id="o1"),
    )
    assert ollama_requests[0] == ollama_requests[1]


def test_failed_run_trace_and_summary_do_not_persist_exception_secret(tmp_path):
    secret = "Bearer ultra-sensitive-token-value"
    logger = JsonlRunAuditLogger(root=tmp_path, run_id="security")
    request = {
        "product": {"name": "Confidential Product", "pitch": "private product pitch"},
        "population_mode": "small",
        "dialogue_mode": "economy",
        "rounds": 1,
        "seed": 42,
    }

    exc = RuntimeError(f"upstream exploded with {secret}")
    emit_run_failed(logger, exc)
    finalize_run_audit(
        logger,
        status="failed",
        request=request,
        warnings=("RuntimeError: backend processing failed",),
    )

    combined = logger.jsonl_path.read_text(encoding="utf-8") + logger.summary_path.read_text(
        encoding="utf-8"
    )
    assert secret not in combined
    assert "ultra-sensitive-token-value" not in combined
    assert "Run failed during backend processing." in combined
