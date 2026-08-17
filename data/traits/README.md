# Trait Data Contract

ModelCouncil uses editable Excel workbooks as the first human-maintained source of synthetic consumer distributions. Python reads them only through `ExcelTraitRepository`; behavioural code never depends on workbook cell coordinates.

## Phase 1 workbook set

```text
data/traits/
├── demographics.xlsx
├── occupations.xlsx
├── personality.xlsx
├── emotions.xlsx
├── economic_traits.xlsx
├── consumer_behaviour.xlsx
├── social_behaviour.xlsx
├── technology.xlsx
├── decision_styles.xlsx
├── archetypes.xlsx
└── compatibility_rules.xlsx
```

Additional workbooks such as `education.xlsx`, `interests.xlsx`, `lifestyle.xlsx`, `relationships.xlsx`, and market-calibration datasets can be introduced later without changing the loader contract.

## Required sheets

### `Traits`

Every workbook uses named columns. These columns are mandatory:

| column | meaning |
|---|---|
| `key` | stable machine identifier; do not casually rename after use |
| `weight` | positive sampling weight; the loader normalizes enabled rows |
| `enabled` | whether the row participates in generation |

`label` is strongly recommended for human-readable text.

Any additional columns are category-specific attributes and are preserved by the loader in `TraitValue.attributes`. Examples include `logicality`, `income_min`, `technology_adoption`, `message_accuracy`, and `evidence_requirement`.

### `Metadata`

The metadata sheet uses `field` / `value` columns and currently records:

- `schema_version` — Phase 1 workbooks use `1.0`;
- `category` — stable category key;
- `workbook` / purpose notes where present;
- editing and weight-normalization guidance.

If `category` is absent, the loader falls back to the workbook filename stem.

## Current category intent

- `demographics` — age-band/household/urbanity starting profiles;
- `occupations` — occupation priors with minimum age, income range, and technology exposure;
- `personality` — logicality, emotionality, stubbornness, risk, curiosity, sociability;
- `emotions` — optimism, fear, excitement, FOMO, status, security, reactance;
- `economic_traits` — price/discount sensitivity, savings, luxury, value, spending;
- `consumer_behaviour` — brand loyalty, switching, research, quality, convenience, review trust;
- `social_behaviour` — sociability, peer/family influence, social proof, persuasion, message accuracy;
- `technology` — digital adoption, AI familiarity/trust, privacy concern, early adoption;
- `decision_styles` — logic/emotion/social/price decision weights and evidence requirements;
- `archetypes` — optional high-level priors that reference other stable category keys;
- `compatibility_rules` — declarative starting constraints/correlations such as student income caps.

## Loader behavior

`simulation/population/excel_repository.py`:

1. discovers `*.xlsx` files;
2. reads the `Traits` sheet;
3. ignores disabled or non-positive-weight rows;
4. normalizes remaining weights into probabilities;
5. keeps stable key/label values;
6. preserves category-specific columns as attributes;
7. reads optional `Metadata`;
8. validates the complete catalog before use.

The generated population can still use the bootstrap distributions when no Excel repository is supplied. This keeps tests and development independent from external files.

## Rules

1. Behavioral intensities normally use `0..1`; product opinions use `-1..1`.
2. Sampling weights do not need to sum to one.
3. Stable `key` values are machine contracts; labels/descriptions may be edited more freely.
4. Avoid deterministic stereotypes: profiles are priors plus correlated random variation.
5. Impossible combinations belong in compatibility/correlation rules rather than scattered conditional logic.
6. Explicit model assumptions must remain inspectable and versioned.
7. Simulation output must stay labeled synthetic until real-world calibration is performed.
8. Future empirical datasets may calibrate these distributions without changing the `ConsumerAgent` interface.
