# Trait Data Contract

ModelCouncil will use editable Excel workbooks as the first human-maintained source of consumer distributions. The Python simulation must read these through a repository/loader layer; behavioural code must never contain workbook cell coordinates.

## Planned workbooks

```text
data/traits/
├── demographics.xlsx
├── occupations.xlsx
├── income.xlsx
├── education.xlsx
├── personality.xlsx
├── emotions.xlsx
├── decision_styles.xlsx
├── economic_traits.xlsx
├── consumer_behaviour.xlsx
├── social_behaviour.xlsx
├── technology.xlsx
├── interests.xlsx
├── lifestyle.xlsx
├── relationships.xlsx
├── archetypes.xlsx
└── compatibility_rules.xlsx
```

The files are intentionally not generated during initialization because the actual trait catalog will be designed and reviewed before data entry.

## Recommended sheet pattern

Every trait workbook should prefer named columns over positional interpretation.

### `values`

| column | meaning |
|---|---|
| `key` | stable machine identifier |
| `label` | human-readable value |
| `weight` | sampling weight |
| `min_value` | optional numeric lower bound |
| `max_value` | optional numeric upper bound |
| `mean` | optional distribution mean |
| `std` | optional standard deviation |
| `enabled` | whether the value participates in generation |

### `dependencies`

| column | meaning |
|---|---|
| `source_trait` | condition source |
| `operator` | comparison (`eq`, `lt`, `gt`, etc.) |
| `source_value` | condition value |
| `target_trait` | affected trait |
| `effect_type` | shift, multiply, restrict, exclude |
| `effect_value` | effect magnitude |

### `metadata`

Store workbook schema version, description, units, author notes, and last calibration notes.

## Rules

1. Behavioural values should normally be normalized to `0..1` after loading.
2. Sampling weights do not need to sum to one; the loader normalizes them.
3. Impossible combinations are handled by compatibility rules rather than ad hoc `if` statements spread across the simulator.
4. Dependencies are probabilistic unless they represent a true impossible constraint.
5. Every loaded workbook will eventually be validated before a simulation starts.
6. The simulation output must record a trait-data version/hash for reproducibility.
7. Real empirical datasets can later replace or calibrate individual distributions without changing the `ConsumerAgent` contract.
