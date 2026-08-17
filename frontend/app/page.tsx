import Link from "next/link";

export default function HomePage() {
  return (
    <div className="page">
      <section className="hero">
        <h1>Watch a product idea move through a synthetic society.</h1>
        <p>
          ModelCouncil generates heterogeneous consumer agents, places them in a
          similarity-driven social network, lets selected neighbours converse, and
          tracks how beliefs, confidence, trust, and purchase intent change over time.
        </p>
        <div className="actions">
          <Link className="button" href="/simulate">
            Create simulation
          </Link>
          <a className="button secondary" href="http://127.0.0.1:8000/docs" target="_blank" rel="noreferrer">
            Inspect API
          </a>
        </div>
      </section>

      <section className="grid3" aria-label="System overview">
        <article className="panel">
          <h2>Structured population</h2>
          <p>
            Consumer identity comes from explicit traits, distributions, correlations,
            memories, relationships, and reproducible random seeds rather than a prompt-only persona.
          </p>
        </article>
        <article className="panel">
          <h2>Social conversation</h2>
          <p>
            KNN defines likely neighbours. A separate scheduler decides who actually talks each round,
            while a shared LLM gives selected conversations natural language.
          </p>
        </article>
        <article className="panel">
          <h2>Auditable dynamics</h2>
          <p>
            Conversation effects are aggregated synchronously by topic before opinions and purchase intent
            are recomputed, avoiding last-speaker and iteration-order bias.
          </p>
        </article>
      </section>
    </div>
  );
}
