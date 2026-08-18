import json

import httpx
import pytest

from simulation.llm.ollama import OllamaProvider


@pytest.mark.asyncio
async def test_ollama_provider_sends_nonstreaming_json_chat_without_auth():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        captured["authorization"] = request.headers.get("Authorization")
        captured["body"] = json.loads(request.content.decode("utf-8"))
        return httpx.Response(
            200,
            json={
                "model": "qwen3:8b",
                "message": {
                    "role": "assistant",
                    "content": '{"conversation":[{"speaker":"A","text":"Useful."},{"speaker":"B","text":"Price matters."}]}'
                },
                "prompt_eval_count": 120,
                "eval_count": 20,
                "done": True,
            },
        )

    provider = OllamaProvider(
        base_url="http://127.0.0.1:11434",
        model="qwen3:8b",
        transport=httpx.MockTransport(handler),
    )

    schema = {
        "type": "object",
        "properties": {
            "conversation": {
                "type": "array",
                "minItems": 2,
                "maxItems": 2,
            }
        },
        "required": ["conversation"],
    }
    response = await provider.generate_json(
        system_prompt="system",
        user_prompt="user",
        max_tokens=320,
        json_schema=schema,
    )

    assert captured["path"] == "/api/chat"
    assert captured["authorization"] is None
    assert captured["body"]["model"] == "qwen3:8b"
    assert captured["body"]["stream"] is False
    assert captured["body"]["format"] == schema
    assert captured["body"]["options"]["temperature"] == pytest.approx(0.65)
    assert captured["body"]["options"]["num_predict"] == 320
    assert captured["body"]["options"]["num_ctx"] == 2048
    assert captured["body"]["messages"] == [
        {"role": "system", "content": "system"},
        {"role": "user", "content": "user"},
    ]
    assert response.data["conversation"][0]["speaker"] == "A"
    assert response.model == "qwen3:8b"
    assert response.usage.prompt_tokens == 120
    assert response.usage.prompt_cache_hit_tokens == 0
    assert response.usage.prompt_cache_miss_tokens == 120
    assert response.usage.completion_tokens == 20
    assert response.usage.total_tokens == 140
    assert response.latency_ms >= 0


@pytest.mark.asyncio
async def test_ollama_provider_rejects_invalid_structured_content():
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "model": "qwen3:8b",
                "message": {"role": "assistant", "content": "not-json"},
                "prompt_eval_count": 1,
                "eval_count": 1,
            },
        )

    provider = OllamaProvider(
        model="qwen3:8b",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(ValueError, match="structured response"):
        await provider.generate_json(
            system_prompt="system",
            user_prompt="user",
        )
