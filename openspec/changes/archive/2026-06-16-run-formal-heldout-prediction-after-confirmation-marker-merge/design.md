## Context

The previous phase merged 12 reviewed form-fill confirmation-marker extension candidates into the formal public sample. The current committed manifest is `public-sample-20260616T074315Z` with 98 seed rows, 252 SFT rows, 850 DPO pairs, and split counts of train 114, dev 69, and test 69.

Existing reports under `reports/public-sample/a100-formal-public-heldout-prediction/` summarize prediction-only evidence from the earlier formal public sample boundary. Reusing or overwriting that directory would blur the difference between the old held-out set and the new post-merge set.

## Goals / Non-Goals

**Goals:**

- Run prediction-only dev/test evaluation against the current formal public sample manifest.
- Keep all private A100 runtime details, adapters, checkpoints, raw logs, caches, and private paths outside git.
- Commit only sanitized public-sample artifacts: predictions, prediction metadata or sidecars when available, metrics, failure slices, manifest/report, leak-scan output, and a Human Brief.
- Make the boundary change explicit: results may be compared as current evidence, but not as a clean apples-to-apples improvement over the prior formal held-out metrics.

**Non-Goals:**

- No SFT, DPO, GRPO, adapter continuation, prompt update, evaluator relaxation, semantic-equivalence scoring, prediction repair, prediction replacement, or prediction re-score.
- No checkpoint or adapter release.
- No production readiness, public full-corpus release, private-corpus generalization, or live-browser benchmark claim.
- No mutation of the formal public sample during this phase.

## Decisions

1. **Publish to a distinct evidence directory.**
   - Decision: write the post-merge run under a new path such as `reports/public-sample/a100-formal-public-heldout-prediction-after-confirmation-marker-merge/`.
   - Rationale: the current manifest has a different held-out boundary; preserving the older directory avoids accidental direct comparison.
   - Alternative considered: overwrite `reports/public-sample/a100-formal-public-heldout-prediction/`. Rejected because it would obscure which manifest produced the earlier metrics.

2. **Use the existing selected private adapter.**
   - Decision: reuse the adapter referenced by the formal-heldout prediction configs unless preflight shows it is unavailable.
   - Rationale: the phase isolates the data-boundary change and avoids introducing new training variables.
   - Alternative considered: train or fine-tune after the merge. Rejected because the next evidence question is prediction-only evaluation against the new manifest.

3. **Fail closed when A100 execution is not safe.**
   - Decision: if no idle GPU, adapter path, private override, or remote environment is safely available, publish blocked evidence rather than fabricate metrics.
   - Rationale: the project values evidence integrity over filling a report slot.
   - Alternative considered: fixture-mode or gold-contract predictions. Rejected because they would not measure the private adapter.

## Risks / Trade-offs

- **Boundary confusion** -> Mitigation: report the manifest id, split counts, prior-evidence path, and a clear warning that prior metrics used a different formal sample boundary.
- **Private runtime leakage** -> Mitigation: sanitize copied artifacts, commit no private override, run leak scan, and use placeholders in public configs/reports.
- **GPU contention** -> Mitigation: inspect `nvidia-smi`, choose only a clearly idle GPU, and stop if placement is unsafe.
- **Metrics regress or remain weak** -> Mitigation: report observed values directly; do not frame prediction-only evidence as recovery or production readiness.
