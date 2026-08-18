"use client";

import { useEffect, useState } from "react";

import { fetchLlmProviders } from "@/lib/api";
import type {
  LlmProviderDescriptor,
  LlmSelection,
} from "@/types/llm-provider";

interface FullLiveProviderSelectorProps {
  onSelectionChange: (selection: LlmSelection | null) => void;
}

function formatBytes(value: number | null) {
  if (value === null) return null;
  const gb = value / 1_000_000_000;
  return `${gb >= 10 ? gb.toFixed(0) : gb.toFixed(1)} GB`;
}

function chooseDefault(providers: LlmProviderDescriptor[]) {
  const deepseek = providers.find(
    (provider) => provider.id === "deepseek" && provider.available && provider.models.length,
  );
  return deepseek ?? providers.find((provider) => provider.available && provider.models.length) ?? null;
}

function resolveSelection(
  providers: LlmProviderDescriptor[],
  preferredProviderId = "",
  preferredModelId = "",
): LlmSelection | null {
  const preferredProvider = providers.find(
    (provider) =>
      provider.id === preferredProviderId && provider.available && provider.models.length,
  );
  const provider = preferredProvider ?? chooseDefault(providers);
  if (!provider) return null;

  const preferredModel = provider.models.find((model) => model.id === preferredModelId);
  const model = preferredModel ?? provider.models[0] ?? null;
  return model ? { provider, model } : null;
}

export function FullLiveProviderSelector({
  onSelectionChange,
}: FullLiveProviderSelectorProps) {
  const [providers, setProviders] = useState<LlmProviderDescriptor[]>([]);
  const [selectedProviderId, setSelectedProviderId] = useState("");
  const [selectedModelId, setSelectedModelId] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  function applyCatalog(
    nextProviders: LlmProviderDescriptor[],
    preferredProviderId = "",
    preferredModelId = "",
  ) {
    const selection = resolveSelection(
      nextProviders,
      preferredProviderId,
      preferredModelId,
    );
    setProviders(nextProviders);
    setSelectedProviderId(selection?.provider.id ?? "");
    setSelectedModelId(selection?.model.id ?? "");
    onSelectionChange(selection);
  }

  useEffect(() => {
    let disposed = false;

    fetchLlmProviders()
      .then((catalog) => {
        if (disposed) return;
        const selection = resolveSelection(catalog.providers);
        setProviders(catalog.providers);
        setSelectedProviderId(selection?.provider.id ?? "");
        setSelectedModelId(selection?.model.id ?? "");
        setError(null);
        onSelectionChange(selection);
      })
      .catch((caught) => {
        if (disposed) return;
        setProviders([]);
        setSelectedProviderId("");
        setSelectedModelId("");
        setError(
          caught instanceof Error
            ? caught.message
            : "Unable to load language providers from ModelCouncil API.",
        );
        onSelectionChange(null);
      })
      .finally(() => {
        if (!disposed) setLoading(false);
      });

    return () => {
      disposed = true;
    };
  }, [onSelectionChange]);

  async function refreshProviders() {
    setLoading(true);
    setError(null);
    try {
      const catalog = await fetchLlmProviders();
      applyCatalog(catalog.providers, selectedProviderId, selectedModelId);
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Unable to refresh language providers from ModelCouncil API.",
      );
    } finally {
      setLoading(false);
    }
  }

  function selectProvider(provider: LlmProviderDescriptor) {
    if (!provider.available || !provider.models.length) return;
    const model = provider.models[0];
    setSelectedProviderId(provider.id);
    setSelectedModelId(model.id);
    onSelectionChange({ provider, model });
  }

  function selectModel(modelId: string) {
    const provider = providers.find((item) => item.id === selectedProviderId) ?? null;
    const model = provider?.models.find((item) => item.id === modelId) ?? null;
    setSelectedModelId(modelId);
    onSelectionChange(provider?.available && model ? { provider, model } : null);
  }

  const selectedProvider =
    providers.find((provider) => provider.id === selectedProviderId) ?? null;
  const selectedModel =
    selectedProvider?.models.find((model) => model.id === selectedModelId) ?? null;
  const modelMeta = selectedModel
    ? [
        selectedModel.parameter_size,
        formatBytes(selectedModel.size_bytes),
        selectedModel.quantization,
      ].filter(Boolean)
    : [];

  return (
    <section className="fullLiveProviderModule" aria-labelledby="full-live-source-title">
      <div className="fullLiveProviderHeader">
        <div>
          <span className="techLabel">Language source / Full Live</span>
          <h3 id="full-live-source-title">Select model source</h3>
        </div>
        <button
          className="button secondary fullLiveRefreshButton"
          type="button"
          onClick={() => void refreshProviders()}
          disabled={loading}
        >
          {loading ? "Scanning…" : "Refresh providers"}
        </button>
      </div>

      {error ? <div className="fullLiveProviderError" role="alert">{error}</div> : null}

      <div className="fullLiveProviderChoices" role="radiogroup" aria-label="Language provider">
        {providers.map((provider) => {
          const selected = provider.id === selectedProviderId;
          return (
            <label
              key={provider.id}
              className={`fullLiveProviderChoice ${selected ? "isSelected" : ""} ${provider.available ? "" : "isDisabled"}`}
            >
              <input
                type="radio"
                name="full-live-provider"
                value={provider.id}
                checked={selected}
                disabled={!provider.available || !provider.models.length}
                onChange={() => selectProvider(provider)}
              />
              <span className="fullLiveProviderChoiceBody">
                <strong>{provider.label}</strong>
                <span className="mono">{provider.kind === "local" ? "LOCAL COMPUTE" : "CLOUD API"}</span>
                <small>{provider.status_message}</small>
              </span>
            </label>
          );
        })}
      </div>

      {!loading && providers.length === 0 ? (
        <p className="fullLiveProviderEmpty">No provider catalog was returned by the backend.</p>
      ) : null}

      {selectedProvider ? (
        <div className="fullLiveModelWell">
          <label htmlFor="full-live-model">Model</label>
          <select
            id="full-live-model"
            value={selectedModelId}
            onChange={(event) => selectModel(event.target.value)}
            disabled={!selectedProvider.available || !selectedProvider.models.length}
          >
            {selectedProvider.models.map((model) => (
              <option key={model.id} value={model.id}>
                {model.label}
              </option>
            ))}
          </select>
          <div className="fullLiveModelMeta">
            <span>{selectedProvider.kind === "local" ? "Runs through local Ollama" : "External cloud API"}</span>
            {modelMeta.length ? <span className="mono">{modelMeta.join(" · ")}</span> : null}
          </div>
        </div>
      ) : null}

      {!loading && providers.some((provider) => provider.id === "ollama" && !provider.reachable) ? (
        <div className="fullLiveOllamaHint">
          Ollama is not reachable. Start the local Ollama service outside ModelCouncil, then press Refresh providers.
        </div>
      ) : null}
    </section>
  );
}
