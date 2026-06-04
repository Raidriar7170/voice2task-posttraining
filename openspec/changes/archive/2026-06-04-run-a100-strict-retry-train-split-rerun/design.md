## Context

The current project stage remains first-phase speech-to-contract normalization. The latest local phase fixed the retry path so a valid-looking JSON fragment inside Markdown/prose no longer becomes a successful retry. The previous A100 required-field repair rerun produced three train predictions, all schema-invalid, with retry attempts recorded as `json_fragment_object`. This phase tests the smallest remote question left open: whether the current strict retry/canonical prompt changes train-split prediction evidence when run against the existing private adapter.

## Goals / Non-Goals

**Goals:**

- Use the existing required-field repair private adapter for a prediction-only rerun on A100.
- Run only public-sample train rows.
- Record raw attempt schema validity, retry attempt schema validity, validated output source, final contract metrics, and constrained-decoding diagnosis separately.
- Import only sanitized public-safe artifacts into the repo.
- Preserve invalid, partial, non-JSON, path-like, Markdown/prose-wrapped, or wrong-contract outputs as observed model evidence.

**Non-Goals:**

- No new training run, no DPO run, no GRPO/rule reward stage, no hyperparameter sweep, no private-corpus training, no generic chat fine-tuning, no skill routing, no GUI action policy learning, no checkpoint release, no adapter release, no production-readiness claim, no held-out dev/test generalization claim, and no live-browser benchmark improvement claim.

## Decisions

1. **Prediction-only instead of retraining.**
   - Rationale: the strict retry repair changed prediction/retry acceptance behavior, not the SFT objective or target data.
   - Alternative considered: train another adapter. Rejected as unnecessary compute before testing the changed decoder path.

2. **Create a new evidence directory.**
   - Rationale: the required-field rerun remains the pre-strict-retry baseline.
   - Alternative considered: overwrite prior evidence. Rejected because it would blur before/after provenance.

3. **Keep raw, retry, and validated outputs separate.**
   - Rationale: strict retry may reduce false positives while still leaving raw model output invalid.
   - Alternative considered: report only final predictions. Rejected because it can hide whether recovery came from retry or raw generation.

4. **Use private A100 overrides and commit only sanitized evidence.**
   - Rationale: adapter paths, raw logs, host details, caches, and private overrides are not public artifacts.
   - Alternative considered: commit command logs for reproducibility. Rejected by the public/private boundary.

## Risks / Trade-offs

- [Risk] The previous adapter path is unavailable on A100 -> Mitigation: stop blocked; do not fabricate fixture evidence.
- [Risk] Strict retry rejects all retries and metrics remain 0/3 -> Mitigation: report as honest failure and keep diagnosis artifacts.
- [Risk] Retry succeeds and gets overclaimed -> Mitigation: preserve raw/retry/validated source fields and keep `generalization_claim=false`.
- [Risk] Sanitization hides useful debugging detail -> Mitigation: keep raw logs private and commit prompt hashes, decoded summaries, generation traces, metrics, and failure slices.
