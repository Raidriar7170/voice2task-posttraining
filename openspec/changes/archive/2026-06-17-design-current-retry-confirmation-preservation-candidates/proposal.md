## Why

The current-train-split SFT retry recovered dev safety outcomes but introduced
confirmation regressions, especially on `blocked_payment` rows where the retry
changed `confirmation_required=true` into `false`. Before any more training,
the project needs a bounded, reviewable candidate design that preserves safety
recovery without normalizing away confirmation behavior.

## What Changes

- Add a design-only evidence pack for current-retry confirmation-preservation
  candidates derived from the committed trade-off diagnosis.
- Identify candidate families and target sketches for rows where safety
  recovered or remained correct but confirmation regressed.
- Record rejected drift sketches so future materialization can avoid changing
  `blocked/deny` rows into `form_fill/fill_form`, `clarify/clarify`, or
  `confirmation_required=false` variants.
- Refresh `CONTEXT.md`, `reports/final_status.md`, and a concise Chinese Human
  Brief with the candidate-design result and claim boundaries.
- Do not materialize new seed rows, rebuild public sample artifacts, train,
  run DPO/GRPO, generate predictions, change prompts, or change evaluator
  metrics in this phase.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `voice2task-dataset-preparation`: add a requirement for publishing
  public-safe current-retry confirmation-preservation candidate designs before
  any candidate materialization or further retry training.

## Impact

- Affected code: public report/evidence generation helpers and report CLI if a
  reusable writer is needed.
- Affected docs/evidence: `CONTEXT.md`, `reports/final_status.md`,
  `reports/public-sample/`, `docs/human-briefs/`, and OpenSpec archives.
- No dependency, model, checkpoint, adapter, remote runtime, prompt, evaluator,
  public manifest, or dataset-builder behavior changes are intended.
- Non-goals: generic chat fine-tuning, skill routing, GUI action policy
  learning, first-phase GRPO, public full-corpus release, checkpoint/adapter
  release, live-browser benchmark claims, and production-readiness claims.
