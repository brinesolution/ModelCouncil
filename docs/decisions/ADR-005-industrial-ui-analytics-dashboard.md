# ADR-005 — Industrial UI System and Dependency-Free Analytics Dashboard

**Status:** Accepted locally  
**Date:** 2026-08-17

## Context

ModelCouncil had a functional but visually generic light UI and only a small number of bespoke SVG visualizations. The project now needs a coherent portfolio-grade product identity plus richer analytics without turning the frontend into a dependency-heavy chart application.

## Decision

1. Use a centralized **industrial-skeuomorphic / industrial-realism** visual system across Home, Simulation, and Results.
2. Keep a predominantly cool light graphite chassis with dark technical display surfaces and a restrained red accent family.
3. Preserve a consistent top-left lighting model for raised/recessed shadows and physical interaction states.
4. Keep the frontend on the existing Next.js + React + plain CSS architecture; do not introduce Tailwind solely for this redesign.
5. Implement the initial analytics dashboard using focused dependency-free SVG/HTML components rather than a chart library.
6. Render exactly six semantic analytics views in a 3×2 desktop matrix:
   - final sentiment composition;
   - purchase-intent distribution;
   - opinion + purchase trend;
   - conversation volume;
   - topic conversation pressure;
   - influence vs purchase intent.
7. Keep the network replay as a separate full-width signature visualization below the six-chart matrix.
8. Add backend analytics only where the current response cannot safely derive the data: full-population purchase bins and full-ledger topic pressure.

## Rationale

- The project currently needs a small fixed family of charts, so a chart dependency is unnecessary.
- Shared CSS/SVG primitives keep bundle size and visual styling under direct control.
- The industrial physical metaphor matches ModelCouncil's “synthetic society control system” product character better than generic SaaS cards.
- Separating dark technical instruments from the light chassis provides contrast without turning the entire product into a dark-mode interface.
- Backend-derived full-population analytics avoid misleading chart values based only on the 80-agent browser network sample.

## Analytics semantics

Purchase intent bins:

- low: `< 0.35`;
- medium: `0.35 <= value <= 0.70`;
- high: `> 0.70`.

Topic pressure:

```text
sum(abs(message stance) * argument strength)
```

for each canonical topic, normalized by the highest topic score in the run.

This metric is explicitly **relative conversation pressure**, not validated causal importance.

## Consequences

Positive:

- one visual language across the current site;
- no extra runtime chart dependency;
- analytics remain auditable and data-backed;
- responsive dashboard can be controlled precisely;
- red remains a functional signal rather than decorative saturation.

Tradeoffs:

- bespoke SVG charts require more local code than a chart package;
- tooltips/interactions are intentionally basic in this interphase;
- browser-level visual QA still needs a browser/Playwright-capable environment or manual screenshot review.

## Future changes

A chart library may be reconsidered if later requirements add zooming, brushing, large datasets, complex tooltips, stacked time series, or many new chart families. Such a change should be justified by a new ADR rather than added opportunistically.
