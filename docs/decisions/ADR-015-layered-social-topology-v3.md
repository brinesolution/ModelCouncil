# ADR-015 — Layered Social Topology V3

**Status:** Accepted / implemented locally  
**Date:** 2026-08-22

## Context

K-map V2 repaired the original purchase-trait KNN topology by separating persistent social attributes from product response, introducing heterogeneous target degree, structured weak ties, directional trust, and slow relationship evolution.

V2 still inferred community from coarse similarity. Two software professionals could receive occupational community affinity without sharing a workplace, and two consumers with the same household tendency could receive household-like affinity without living together. The graph therefore had socially grounded similarity but not persistent relational membership.

V3 introduces explicit synthetic social structure while preserving the existing engine and graph interfaces.

## Decision

### 1. Membership is population state, not an edge-side guess

`ConsumerContext` now contains `SocialMembershipContext`:

```text
region_id
city_id
city_tier
locality_id
household_id
workplace_id
education_id
online_interest_ids
```

Memberships are assigned once in a deterministic population-wide second pass after individual traits are generated. Both Excel-backed and bootstrap populations use the same assignment stage.

Membership assignment is independent from the active product and does not use `product_need`, current beliefs, purchase intent, or other run-specific product state.

### 2. Geography is deliberately abstract

The current trait source contains urbanity but not validated real region/city records. V3 therefore emits structural IDs such as:

```text
region-000
city-t1-0003
city-t1-0003:locality-002
```

These IDs create geographic clustering and local bridges. They must not be interpreted as named real places or statistically calibrated geographic populations.

City tier is correlated with existing urbanity. Exact region/city/locality membership remains seeded synthetic structure.

### 3. The graph is multiplex but remains one NetworkX graph

A single edge can contain multiple contexts:

```text
social_layers
layer_strengths
primary_layer
interaction_opportunity
formation_sources
```

Supported normal layers are:

```text
household
workplace
local
education
online
social_affinity
triadic_closure
```

Weak contacts use `weak_bridge` while retaining their more specific formation source such as `weak_two_hop`.

The graph remains undirected for relationship existence while trust remains directional.

### 4. Large groups are not cliques

Only small household cohorts are fully connected.

Hard undirected formation caps are applied to represented large-group contacts:

```text
workplace <= 4
education <= 5
local     <= 3
online    <= 4
```

The total number of explicit contacts is also bounded relative to each consumer's heterogeneous target social degree. This prevents a low-social consumer from receiving every layer's maximum independently.

After explicit contacts, V2 affinity candidate search fills remaining target capacity. Triadic closure and weak bridges run afterward.

### 5. Exact membership and coarse similarity are distinct

V3 distinguishes:

```text
same occupation       != same workplace
same household tendency != same household
same city             != same locality
```

Coarse occupation, life stage, age, language, and locale remain secondary affinity signals. Exact membership has larger weight.

### 6. Layer priors affect familiarity, not opinion agreement

Starting relationship strength and interaction opportunity are ordered approximately as:

```text
household > education/workplace > local > online > affinity > weak bridge
```

Multi-layer pairs receive a bounded familiarity/opportunity bonus.

No layer forces agreement. Household or workplace contacts can carry strong disagreement through the normal opinion model.

### 7. Scheduler selection now includes interaction opportunity

V3 candidate scoring uses:

```text
similarity               0.18
relationship             0.24
interaction opportunity  0.18
product salience         0.22
sociability              0.18
+ bounded informational difference
```

This reduces the scheduler's previous dependence on abstract similarity and allows frequently interacting relationship contexts to matter directly.

V2's explicit weak-tie exploration path remains. The current default remains `0.22` because measured V3 weak-tie conversation share remains in the intended ordinary-product range.

### 8. Structural relationships receive slow-evolution floors

V2 relationship/trust evolution remains. V3 adds bounded relationship floors by strongest persistent layer so a structural household/workplace tie cannot become equivalent to a random acquaintance after a small number of simulated conversations.

### 9. Network diagnostics expose layer composition

`NetworkDistributionMetrics` now includes:

```text
household/workplace/local/education/online edge share
affinity edge share
multi-layer edge share
household/workplace/education/online membership coverage
```

The API also exposes sampled edge `social_layers`/`primary_layer` and conversation-agent membership profiles.

## Calibration evidence

Fresh Excel-backed topology diagnostics from the completed V3 verification campaign:

```text
250 agents, k=10
edges             1,436
degree P10/50/90  6 / 10 / 18
max degree        51
clustering         0.253
components         1
weak edges         4.7%
graph build        0.30s
multi-layer edges  63.4%

1,000 agents, k=14
edges             8,156
degree P10/50/90  9 / 15 / 25.1
max degree        65
clustering         0.167
components         1
weak edges         4.8%
graph build        2.17s
multi-layer edges  37.4%

5,000 agents, k=18
edges             51,256
degree P10/50/90  11 / 19 / 32
max degree        81
clustering         0.127
components         1
weak edges         4.8%
graph build        18.57s
multi-layer edges  21.8%
```

Times are local-machine diagnostics, not service-level guarantees. The 5,000-agent graph remains below the V3 density-growth guardrail and is fully connected. Explicit-layer shares at 1,000 agents were approximately 10.1% household, 22.1% workplace, 25.8% local, 7.9% education, and 24.0% online; an edge may belong to more than one layer, so these percentages do not sum to 100%.

Six-seed Excel-backed 250-agent / 10-round behavior diagnostics produced:

```text
good product:  mean opinion +0.262, purchase 0.578, below-zero share 0.9%
mixed product: mean opinion +0.093, purchase 0.486, below-zero share 19.7%
bad product:   mean opinion -0.071, purchase 0.292, below-zero share 73.4%

selected weak-tie share  ~10.1–10.2%
repeat-pair rate          ~11.9–12.2%
zero-participation share  ~1.8–2.3%
mean opinion movement     ~0.0118–0.0133
```

Primary-layer conversation exposure was stable across those products: workplace about 25%, household about 18%, online about 15%, local about 11%, weak bridges about 10%, social-affinity about 12%, education about 7%, and triadic-closure-first edges about 2%. All explicit layers appeared in selected conversations. These are synthetic calibration diagnostics, not real-market forecasts.

## Consequences

### Positive

- Network relationships now have persistent relational explanations.
- Same occupation no longer means same workplace.
- Household, workplace, local, education, and online pathways can produce different diffusion paths.
- `k` remains a candidate/fill scale instead of a literal number of friends or conversations.
- Layer metadata is auditable and available through the API.
- Directional trust and synchronous opinion semantics are preserved.
- Large-group edge growth is bounded.

### Trade-offs

- Synthetic geography is structural rather than empirically geographic.
- Household/workplace/institution IDs represent the portion of those groups present in the synthetic sample, not complete real-world household or organization size.
- Small populations naturally have more layer overlap because the same represented consumers share more nested contexts. Standard/large populations show substantially lower multi-layer edge share.
- V3 graph construction is heavier than V2 because it performs population-scoped membership formation plus multiple bounded layer passes; the completed 5,000-agent local diagnostic builds the graph in about 18.6 seconds.
- Coefficients remain designed model parameters requiring empirical calibration before predictive claims.

## Rejected alternatives

### Five independent graph objects

Rejected for V3 because it would duplicate scheduler, trust, evolution, replay, and audit logic. The multiplex edge representation provides the required semantics with less integration risk.

### Infer layers only from edge endpoints

Rejected because memberships would not be persistent population facts and would repeat the conceptual weakness V3 is intended to fix.

### Clique every workplace/locality/online group

Rejected because density and runtime would grow rapidly and because membership in a 90-person represented online cohort does not imply direct relationships with every other member.

### Use named real Indian cities without source data

Rejected because it would imply geographic realism the current trait source does not support.

## Compatibility

- `generate_population()` signature is unchanged.
- `build_knn_graph()` signature is unchanged.
- `ConsumerContext.memberships` has safe defaults.
- Legacy edges lacking `interaction_opportunity` use scheduler fallback behavior.
- Legacy trust still falls back from directional to symmetric `trust` when required.
- No runtime dependency or database migration is introduced.
