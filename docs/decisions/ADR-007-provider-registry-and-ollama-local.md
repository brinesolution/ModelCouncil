# ADR-007: Provider Registry and Ollama Local

**Date:** 2026-08-17  
**Status:** Accepted for the local Phase 2 implementation

## Context

Full Live originally constructed DeepSeek directly. That made the job system cloud-provider-specific and would require branching through the renderer, API, and UI for every additional model source.

The project now needs Ollama Local: when Full Live is selected, ModelCouncil should scan the server machine's downloaded Ollama models, let the user select one, and run every scheduled conversation through that selected local model without changing simulation semantics.

## Decision

Full Live is provider-neutral.

A backend provider catalog exposes stable provider/model descriptors. A provider factory validates an exact `(provider_id, model_id)` selection and returns a concrete implementation of the existing `LLMProvider` protocol plus provider-specific concurrency, pricing, and telemetry capabilities.

Initial providers:

- `deepseek` — configured cloud API/model;
- `ollama` — server-local Ollama native API/model discovery.

The browser never connects directly to Ollama. FastAPI owns discovery and model execution.

Ollama discovery uses the configured `OLLAMA_BASE_URL` and native `GET /api/tags`. Ollama generation uses native `POST /api/chat`, a bounded `OLLAMA_NUM_CTX` context window (default 2048), and native JSON Schema structured output for conversation payloads. ModelCouncil does not install/start/pull/delete Ollama models.

Provider/model selection appears only for `full_live` in this phase. Economy/Balanced/Full retain existing behavior.

## Consequences

### Positive

- Future providers can register behind catalog/factory boundaries without renderer branches.
- Ollama does not require a DeepSeek key or DeepSeek live-enable flag.
- Selected Ollama models are revalidated server-side before job creation.
- DeepSeek resolution does not wait for an offline Ollama service.
- The existing semantic-preserving Full Live renderer is reused unchanged.
- UI can distinguish billable cloud execution from local compute.

### Trade-offs

- Provider discovery adds backend/API types and UI state.
- Ollama jobs depend on an Ollama service running on the FastAPI host.
- Local inference performance varies widely by hardware/model.
- Ollama does not expose DeepSeek-equivalent cache-hit token accounting, so the UI labels cache reuse as unavailable for Ollama.

## Safety invariants

- Provider/model choices never change scheduler output or numerical state.
- Browser-supplied arbitrary provider URLs are not allowed.
- API keys remain backend-only.
- Full Live remains uncapped in total scheduled conversations but uses provider-specific bounded concurrency.
- High-call typed acknowledgement remains for both cloud and local providers.

## Local development observation

During implementation, Ollama client `0.17.4` was installed on the Windows development machine. After the local service was enabled, real integration testing exposed two runtime issues: unbounded/default model context allocation could return `memory layout cannot be allocated`, and generic `format: "json"` allowed smaller models such as `gemma3:1b` to echo/truncate the prompt. Bounding `num_ctx` to 2048 and supplying the exact conversation JSON Schema produced stable real renders. Provider-source metadata is also passed explicitly so Ollama transcripts are labeled `ollama`, not the legacy `deepseek` source.
