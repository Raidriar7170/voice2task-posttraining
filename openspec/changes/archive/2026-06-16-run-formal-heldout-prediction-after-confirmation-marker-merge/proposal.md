## Why

The formal public sample now includes 12 form-fill confirmation-marker extension candidates, changing the manifest from `public-sample-20260615T...` style evidence to `public-sample-20260616T074315Z` with 98 seed rows, 252 SFT rows, and 850 DPO pairs. The existing formal held-out prediction metrics were generated before this boundary change, so the next evidence step is a prediction-only rerun against the new manifest without training, evaluator relaxation, or direct overclaiming.

## What Changes

- Run a bounded A100 prediction-only evaluation for the current formal public sample dev/test splits using the existing selected private adapter.
- Publish a new sanitized evidence directory whose name makes the post-confirmation-marker-merge boundary explicit rather than overwriting the earlier `a100-formal-public-heldout-prediction` evidence.
- Record the current manifest id, split counts, prediction metadata, sanitized predictions, metrics, failure slices, and boundary notes for dev and test.
- Preserve strict `contract_exact_match`, strict `slot_f1`, and the contract evaluation ladder as authoritative; keep `slot_f1_soft` diagnostic-only.
- Do not train SFT/DPO/GRPO, mutate datasets, change prompts, relax evaluator metrics, repair/replace predictions, publish adapters/checkpoints, or claim production/live-browser improvement.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `contract-evaluation`: require post-merge formal held-out prediction evidence to use the new manifest id, publish into a distinct evidence directory, and label comparisons against prior formal-heldout metrics as boundary-changed.

## Impact

- Affected configs: formal public held-out dev/test prediction configs may need an evidence-output suffix that distinguishes the post-confirmation-marker-merge run.
- Affected reports: a new public-safe evidence pack under `reports/public-sample/` plus a Human Brief for the phase.
- Affected runtime: one prediction-only A100 run per dev/test split, using the authorized A100 machine and an idle GPU when safe.
- Non-goals: generic chat fine-tuning, skill routing, GUI action policy learning, first-phase GRPO, public release of the full local corpus, new training, evaluator relaxation, prediction repair, checkpoint/adapter release, public full-corpus release, private-corpus generalization, production readiness, or live-browser benchmark claims.
