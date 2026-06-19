## Why

The current formal public sample boundary is now
`public-sample-20260619T090925Z`, but the latest model evidence still targets
the older `public-sample-20260617T152259Z` manifest. A bounded prediction-only
baseline is needed so future diagnosis uses evidence that explicitly binds to
the canonical slot-boundary merged data boundary.

## What Changes

- Prepare a prediction-only baseline for the current canonical-boundary formal
  public sample dev/test splits using the existing private
  `a100-current-train-split-sft-retry` adapter.
- If the A100 environment, idle GPU placement, private adapter, or prediction
  command can be verified safely, generate sanitized dev/test predictions and
  strict contract-ladder metrics for `public-sample-20260619T090925Z`.
- If any prerequisite cannot be verified safely, publish fail-closed blocked
  evidence without fabricated predictions or model-quality metrics.
- Publish a public-safe evidence pack, status-doc updates, and a concise
  Chinese Human Brief.
- Preserve boundaries: no SFT, DPO, GRPO, dataset mutation, prompt change,
  evaluator relaxation, semantic-equivalence scoring, slot normalization,
  prediction repair, checkpoint/adapter release, or model-recovery claim.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `contract-evaluation`: require current canonical-boundary prediction-only
  evidence, or blocked evidence, to bind explicitly to
  `public-sample-20260619T090925Z` and preserve strict metric and public-safety
  claim boundaries.

## Impact

- Affected code:
  - `src/voice2task/training.py`
  - `src/voice2task/reports.py`
  - `src/voice2task/cli/report.py`
  - existing prediction/evaluation helpers as needed
- Affected tests:
  - focused tests for current-boundary prediction config/evidence, blocked
    status, claim boundaries, and leak-scan cleanliness
- Affected artifacts:
  - `configs/` prediction templates if a current-boundary template is needed
  - `reports/public-sample/a100-current-canonical-boundary-prediction-baseline/`
  - `docs/human-briefs/2026-06-19-run-current-canonical-boundary-prediction-baseline.html`
  - `CONTEXT.md`
  - `reports/final_status.md`
- Non-goals:
  - generic chat fine-tuning, skill routing, GUI action policy learning, or
    first-phase GRPO
  - public release of the full local/private corpus
  - new training, optimizer changes, data expansion, prompt changes, evaluator
    definition changes, postprocessor implementation, slot normalization,
    prediction repair, or semantic-equivalence re-scoring
  - checkpoint/adapter publication, production-readiness claims,
    private-corpus generalization claims, public full-corpus release claims, or
    live-browser benchmark improvement claims
