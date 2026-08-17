"use client";

import { FormEvent, useState } from "react";

import { previewSimulation } from "@/lib/api";
import type {
  DialogueMode,
  PopulationMode,
  SimulationPreviewResponse,
} from "@/types/simulation";

const DEFAULT_PITCH =
  "An AI-powered fitness coach that creates personalized workout plans, nutrition guidance, and progress tracking for one monthly subscription.";

export function ProductPitchForm() {
  const [name, setName] = useState("AI Fitness Coach");
  const [category, setCategory] = useState("Fitness Technology");
  const [pitch, setPitch] = useState(DEFAULT_PITCH);
  const [price, setPrice] = useState("999");
  const [populationMode, setPopulationMode] = useState<PopulationMode>("standard");
  const [dialogueMode, setDialogueMode] = useState<DialogueMode>("balanced");
  const [rounds, setRounds] = useState(20);
  const [seed, setSeed] = useState(42);
  const [result, setResult] = useState<SimulationPreviewResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const data = await previewSimulation({
        product: {
          name,
          category,
          pitch,
          price: price.trim() === "" ? null : Number(price),
          currency: "INR",
        },
        population_mode: populationMode,
        dialogue_mode: dialogueMode,
        rounds,
        seed,
      });
      setResult(data);
    } catch (caught) {
      setResult(null);
      setError(caught instanceof Error ? caught.message : "Unable to reach ModelCouncil API.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="simLayout">
      <form className="formPanel" onSubmit={onSubmit}>
        <div className="formGrid">
          <div className="field">
            <label htmlFor="product-name">Product name</label>
            <input id="product-name" value={name} onChange={(event) => setName(event.target.value)} required />
          </div>

          <div className="field">
            <label htmlFor="category">Category</label>
            <input id="category" value={category} onChange={(event) => setCategory(event.target.value)} />
          </div>

          <div className="field">
            <label htmlFor="price">Price (INR)</label>
            <input id="price" type="number" min="0" step="0.01" value={price} onChange={(event) => setPrice(event.target.value)} />
          </div>

          <div className="field">
            <label htmlFor="population">Population</label>
            <select id="population" value={populationMode} onChange={(event) => setPopulationMode(event.target.value as PopulationMode)}>
              <option value="small">Small — 250 agents</option>
              <option value="standard">Standard — 1,000 agents</option>
              <option value="large">Large — 5,000 agents</option>
            </select>
          </div>

          <div className="field full">
            <label htmlFor="pitch">Product pitch</label>
            <textarea id="pitch" value={pitch} onChange={(event) => setPitch(event.target.value)} minLength={10} required />
          </div>

          <div className="field">
            <label htmlFor="dialogue">Dialogue mode</label>
            <select id="dialogue" value={dialogueMode} onChange={(event) => setDialogueMode(event.target.value as DialogueMode)}>
              <option value="economy">Economy</option>
              <option value="balanced">Balanced</option>
              <option value="full">Full dialogue</option>
            </select>
          </div>

          <div className="field">
            <label htmlFor="rounds">Rounds</label>
            <input id="rounds" type="number" min="1" max="200" value={rounds} onChange={(event) => setRounds(Number(event.target.value))} />
          </div>

          <div className="field">
            <label htmlFor="seed">Random seed</label>
            <input id="seed" type="number" min="0" value={seed} onChange={(event) => setSeed(Number(event.target.value))} />
          </div>
        </div>

        <div className="formFooter">
          <span className={`status ${error ? "error" : ""}`}>
            {error ?? "This initialization call does not spend LLM credits."}
          </span>
          <button className="button" type="submit" disabled={loading}>
            {loading ? "Preparing…" : "Preview simulation"}
          </button>
        </div>
      </form>

      <aside className="metricPanel" aria-live="polite">
        <div className="resultHeader">
          <h2>Simulation plan</h2>
          <span className="muted">v0.1</span>
        </div>
        {result ? (
          <>
            <div className="metricList">
              <div className="metric"><span>Population</span><strong>{result.preset.population_size.toLocaleString()}</strong></div>
              <div className="metric"><span>Base K</span><strong>{result.preset.base_k}</strong></div>
              <div className="metric"><span>Max chats / agent / round</span><strong>{result.preset.max_conversations_per_round}</strong></div>
              <div className="metric"><span>Potential initiators / round</span><strong>{Math.round(result.preset.initiator_rate * 100)}%</strong></div>
              <div className="metric"><span>Weak ties</span><strong>{Math.round(result.preset.weak_tie_rate * 100)}%</strong></div>
              <div className="metric"><span>Round duration</span><strong>{result.preset.simulated_minutes_per_round} min</strong></div>
              <div className="metric"><span>Rounds</span><strong>{result.rounds}</strong></div>
              <div className="metric"><span>Dialogue mode</span><strong>{result.dialogue_mode}</strong></div>
              <div className="metric"><span>Seed</span><strong>{result.seed}</strong></div>
            </div>
            <p className="muted">{result.note}</p>
          </>
        ) : (
          <p className="emptyState">
            Enter a product pitch and choose a population mode. The API will return the exact simulation preset that the later graph, conversation, and opinion engines will consume.
          </p>
        )}
      </aside>
    </div>
  );
}
