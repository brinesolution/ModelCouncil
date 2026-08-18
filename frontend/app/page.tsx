import Link from "next/link";

import { PanelDetails } from "@/components/industrial/panel-details";
import { SocietyMonitor } from "@/features/home/society-monitor";

const MODULES = [
  {
    index: "01",
    title: "Structured population",
    text: "Consumer identity comes from explicit traits, distributions, correlations, relationships, and seeded variation rather than prompt-only personas.",
  },
  {
    index: "02",
    title: "Social conversation",
    text: "KNN defines likely neighbours. A separate scheduler decides who actually talks, while selected conversations can be rendered through DeepSeek after semantic state is fixed.",
  },
  {
    index: "03",
    title: "Auditable dynamics",
    text: "Every round freezes state, aggregates topic evidence synchronously, commits one update per agent, and recomputes purchase intent from the resulting beliefs.",
  },
] as const;

const PROCESS_STEPS = [
  ["01", "Pitch input"],
  ["02", "Synthetic population"],
  ["03", "KNN society"],
  ["04", "Conversation rounds"],
  ["05", "Analytics + replay"],
] as const;

export default function HomePage() {
  return (
    <div className="page">
      <section className="homeHero">
        <div className="homeHeroCopy">
          <h1>
            Watch a product idea move through a <strong>synthetic society.</strong>
          </h1>
          <p>
            ModelCouncil generates heterogeneous consumers, connects them through a similarity-driven social network,
            lets selected neighbours converse, and measures how beliefs, confidence, trust, and purchase intent evolve.
          </p>
          <div className="actions">
            <Link className="button" href="/simulate">Run a simulation</Link>
            <a className="button secondary" href="http://127.0.0.1:8000/docs" target="_blank" rel="noreferrer">
              Inspect API
            </a>
          </div>
        </div>
        <SocietyMonitor />
      </section>

      <section className="grid3" aria-label="ModelCouncil system overview">
        {MODULES.map((module) => (
          <article className="panel" key={module.index}>
            <PanelDetails />
            <span className="moduleIndex">{module.index}</span>
            <h2>{module.title}</h2>
            <p>{module.text}</p>
          </article>
        ))}
      </section>

      <section className="processStrip" aria-labelledby="process-title">
        <div className="resultHeader">
          <div>
            <span className="techLabel">Deterministic core / selective language layer</span>
            <h2 id="process-title">From product pitch to replayable market dynamics</h2>
          </div>
        </div>
        <div className="processFlow">
          {PROCESS_STEPS.map(([index, label], position) => (
            <div key={index} className="processContents">
              <div className="processStep">
                <span className="techLabel">Stage {index}</span>
                <strong>{label}</strong>
              </div>
              {position < PROCESS_STEPS.length - 1 ? <span className="processConnector" aria-hidden="true" /> : null}
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
