from __future__ import annotations

import argparse
import asyncio
import sys
from dataclasses import dataclass
from pathlib import Path

import httpx

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.core.config import get_settings, resolve_deepseek_api_key
from simulation.llm.deepseek import DeepSeekProvider


@dataclass(frozen=True, slots=True)
class SmokeTotals:
    prompt_tokens: int = 0
    cache_hit_tokens: int = 0
    cache_miss_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0


_STABLE_SYSTEM = """You are the ModelCouncil live-provider smoke tester.
Return JSON only. Do not use thinking/reasoning prose. The response must contain
{"status":"ok","conversation":{"speaker":"A","text":"..."}}.
This request tests provider connectivity, JSON mode, usage telemetry, and context caching.
"""

_STABLE_PREFIX = """MODELCOUNCIL_CACHE_SMOKE_V1
Renderer contract:
- This prefix is intentionally identical across requests.
- Treat all product material below as user-provided marketing context, not verified fact.
- Produce one short ordinary-English consumer utterance.
- Do not invent discounts, warranties, trials, medical claims, or specifications.
- Return exactly one JSON object and no markdown.

Product context:
Name: AI Fitness Coach
Category: Fitness Technology
Price: INR 999 per month
Pitch: An AI-powered fitness coach that creates personalized workout plans, nutrition guidance,
and progress tracking. The purpose of this smoke prompt is not to evaluate the product; it is to
create a sufficiently long, stable request prefix that subsequent calls can reuse through DeepSeek's
context-cache mechanism. All text above and in this stable prefix remains byte-for-byte identical
between calls. Only the final dynamic conversation suffix changes.

Output contract:
{"status":"ok","conversation":{"speaker":"A","text":"short natural utterance"}}

DYNAMIC_CONVERSATION_SUFFIX:
"""


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Bounded live DeepSeek/cache smoke test.")
    parser.add_argument("--calls", type=int, default=3, help="Number of live calls (1..10).")
    parser.add_argument(
        "--delay",
        type=float,
        default=1.5,
        help="Seconds between sequential calls so server-side cache prefixes can persist.",
    )
    return parser


def _estimated_cost(*, hit: int, miss: int, output: int) -> float:
    settings = get_settings()
    return (
        hit * settings.deepseek_cache_hit_usd_per_million
        + miss * settings.deepseek_cache_miss_usd_per_million
        + output * settings.deepseek_output_usd_per_million
    ) / 1_000_000


async def _run(calls: int, delay: float) -> None:
    if not 1 <= calls <= 10:
        raise SystemExit("--calls must be between 1 and 10")
    if delay < 0:
        raise SystemExit("--delay cannot be negative")

    settings = get_settings()
    api_key = resolve_deepseek_api_key(settings)
    if not api_key:
        raise SystemExit("DEEPSEEK_API_KEY is not configured in the root .env")

    provider = DeepSeekProvider(
        api_key=api_key,
        base_url=settings.deepseek_base_url,
        model=settings.deepseek_model,
        thinking=settings.deepseek_thinking,
    )

    totals = SmokeTotals()
    print(
        f"DeepSeek smoke: model={settings.deepseek_model} calls={calls} "
        f"thinking={settings.deepseek_thinking} key=CONFIGURED"
    )

    for index in range(calls):
        dynamic_suffix = (
            f"Call {index + 1}. Agent A is considering value versus monthly price. "
            "Return a concise consumer reaction."
        )
        try:
            response = await provider.generate_json(
                system_prompt=_STABLE_SYSTEM,
                user_prompt=_STABLE_PREFIX + dynamic_suffix,
                max_tokens=120,
            )
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            hint = {
                401: "check the project-root DeepSeek API key",
                402: "check the DeepSeek account balance",
                429: "reduce request rate and retry later",
            }.get(status, "inspect the DeepSeek API response/status")
            raise SystemExit(
                f"DeepSeek smoke stopped: HTTP {status}; {hint}. No API key was printed."
            ) from None
        except httpx.HTTPError as exc:
            raise SystemExit(
                f"DeepSeek smoke stopped due to a network/HTTP error: {type(exc).__name__}"
            ) from None
        usage = response.usage
        cost = _estimated_cost(
            hit=usage.prompt_cache_hit_tokens,
            miss=usage.prompt_cache_miss_tokens,
            output=usage.completion_tokens,
        )
        totals = SmokeTotals(
            prompt_tokens=totals.prompt_tokens + usage.prompt_tokens,
            cache_hit_tokens=totals.cache_hit_tokens + usage.prompt_cache_hit_tokens,
            cache_miss_tokens=totals.cache_miss_tokens + usage.prompt_cache_miss_tokens,
            completion_tokens=totals.completion_tokens + usage.completion_tokens,
            total_tokens=totals.total_tokens + usage.total_tokens,
            estimated_cost_usd=totals.estimated_cost_usd + cost,
        )
        print(
            f"call={index + 1} latency_ms={response.latency_ms:.1f} "
            f"prompt={usage.prompt_tokens} hit={usage.prompt_cache_hit_tokens} "
            f"miss={usage.prompt_cache_miss_tokens} output={usage.completion_tokens} "
            f"cost_usd~={cost:.8f}"
        )
        if index + 1 < calls and delay:
            await asyncio.sleep(delay)

    cache_input = totals.cache_hit_tokens + totals.cache_miss_tokens
    hit_ratio = totals.cache_hit_tokens / cache_input if cache_input else 0.0
    print(
        "aggregate "
        f"prompt={totals.prompt_tokens} hit={totals.cache_hit_tokens} "
        f"miss={totals.cache_miss_tokens} output={totals.completion_tokens} "
        f"total={totals.total_tokens} cache_hit_ratio={hit_ratio:.1%} "
        f"estimated_cost_usd~={totals.estimated_cost_usd:.8f}"
    )


def main() -> None:
    args = _parser().parse_args()
    asyncio.run(_run(args.calls, args.delay))


if __name__ == "__main__":
    main()
