"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

import { runSimulation } from "@/lib/api";
import {
  WEB_ROUND_LIMITS,
  type DialogueMode,
  type PopulationMode,
} from "@/types/simulation";

const DEFAULT_PITCH =
  "An AI-powered fitness coach that creates personalized workout plans, nutrition guidance, and progress tracking for one monthly subscription.";

const POPULATION_LABELS: Record<PopulationMode, string> = {
  small: "250 agents · K 10",
  standard: "1,000 agents · K 14",
  large: "5,000 agents · K 18",
};

export function ProductPitchForm() {
  const router = useRouter();
  const [name, setName] = useState("AI Fitness Coach");
  const [category, setCategory] = useState("Fitness Technology");
  const [pitch, setPitch] = useState(DEFAULT_PITCH);
  const [price, setPrice] = useState("999");
  const [populationMode, setPopulationMode] = useState<PopulationMode>("standard");
  const [dialogueMode, setDialogueMode] = useState<DialogueMode>("balanced");
  const [rounds, setRounds] = useState(20);
  const [seed, setSeed] = useState(42);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const roundLimit = WEB_ROUND_LIMITS[populationMode];

  function handlePopulationChange(nextMode: PopulationMode) {
    setPopulationMode(nextMode);
    setRounds((current) => Math.min(current, WEB_ROUND_LIMITS[nextMode]));
  }

  function handleRoundsChange(nextValue: number) {
    setRounds(Math.min(Math.max(nextValue, 1), roundLimit));
  }

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const data = await runSimulation({
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
      window.sessionStorage.setItem(
        "modelcouncil:last-simulation",
        JSON.stringify(data),
      );
      router.push("/simulations/result");
    } catch (caught) {
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
            <select
              id="population"
              value={populationMode}
              onChange={(event) => handlePopulationChange(event.target.value as PopulationMode)}
            >
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
            <input
              id="rounds"
              type="number"
              min="1"
              max={roundLimit}
              value={rounds}
              onChange={(event) => handleRoundsChange(Number(event.target.value))}
            />
            <span className="muted">Maximum for this population: {roundLimit} rounds.</span>
          </div>

          <div className="field">
            <label htmlFor="seed">Random seed</label>
            <input id="seed" type="number" min="0" value={seed} onChange={(event) => setSeed(Number(event.target.value))} />
          </div>
        </div>

        <div className="formFooter">
          <span className={`status ${error ? "error" : ""}`}>
            {error ?? "Phase 1 runs deterministic semantic conversations and spends no LLM credits."}
          </span>
          <button className="button" type="submit" disabled={loading}>
            {loading ? "Running society…" : "Run simulation"}
          </button>
        </div>
      </form>

      <aside className="metricPanel">
        <div className="resultHeader">
          <h2>Run configuration</h2>
          <span className="muted">Phase 1</span>
        </div>
        <div className="metricList">
          <div className="metric"><span>Population</span><strong>{POPULATION_LABELS[populationMode]}</strong></div>
          <div className="metric"><span>Rounds</span><strong>{rounds}</strong></div>
          <div className="metric"><span>Round limit</span><strong>{roundLimit}</strong></div>
          <div className="metric"><span>Simulated time</span><strong>{rounds * 5} min</strong></div>
          <div className="metric"><span>Max chats / agent / round</span><strong>2</strong></div>
          <div className="metric"><span>Potential initiators</span><strong>20%</strong></div>
          <div className="metric"><span>Weak social ties</span><strong>5%</strong></div>
          <div className="metric"><span>Dialogue setting</span><strong>{dialogueMode}</strong></div>
          <div className="metric"><span>Seed</span><strong>{seed}</strong></div>
        </div>
        <p className="muted">
          Dialogue mode is preserved in the experiment contract. In Phase 1, all interactions use the deterministic semantic engine; DeepSeek rendering is layered on after this simulation path is verified.
        </p>
      </aside>
    </div>
  );
}
