## Why

The layered evaluator and residual diagnosis show that strict exact match is
not the only weak surface: executable contract pass rate and normalized slot
metrics are also low, while JSON/schema validity and route/task-type behavior
are comparatively stable. Before any new training, data merge, or evaluator
change, the project needs a public-safe target-selection report that ranks
failure families and chooses at most two bounded remediation directions.

## What Changes

- Add an analysis-only remediation target-selection report under
  `reports/public-sample/remediation-target-selection/`.
- Read the committed layered-eval and latest residual-diagnosis artifacts
  without overwriting historical diagnosis, scaled residual, or strict
  evaluator artifacts.
- Rank dev/test residual failure families, attach public-safe examples, map
  frequent families to remediation strategies, and choose at most two next
  remediation targets.
- Write a reusable `recommended-next-change.md` that can seed the following
  OpenSpec phase while preserving claim boundaries.
- Add focused tests for artifact ingestion, family aggregation, strategy
  selection, safety prioritization, output files, and public-safe reporting.
- Non-goals: generic chat fine-tuning, skill routing, GUI action policy
  learning, first-phase GRPO, public release of the full local corpus, training,
  prediction reruns, DPO expansion, LoRA/base-model changes, evaluator
  relaxation, LLM judge use, semantic equivalence scoring, prediction repair,
  checkpoint/adapter release, held-out recovery claims, production-readiness
  claims, safety-readiness claims, and live-browser benchmark claims.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `contract-evaluation`: add public-safe remediation target-selection evidence
  from layered evaluator and residual diagnosis artifacts.

## Impact

- New or updated report-generation code under `src/voice2task/`.
- New public-safe report artifacts under
  `reports/public-sample/remediation-target-selection/`.
- New or updated tests under `tests/`.
- New OpenSpec archive material and a Human Brief HTML for this phase.
