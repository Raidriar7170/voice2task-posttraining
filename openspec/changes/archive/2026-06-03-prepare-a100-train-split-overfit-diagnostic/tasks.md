## 1. Diagnostic Configuration

- [x] 1.1 Add a public-safe train-split diagnostic prediction config template with `prediction_split=train`, `overfit_diagnostic=true`, placeholder private paths, and explicit private-override requirements.
- [x] 1.2 Update the A100 runbook to describe the diagnostic as a gated train-internal overfit sanity check, not a benchmark or release.

## 2. Prediction Evidence Sidecars

- [x] 2.1 Add failing tests for prompt snapshot, sanitized raw decoded summary, generation trace, and metadata links without changing prediction values.
- [x] 2.2 Implement sidecar generation for trained-adapter prediction exports, including bounded sanitized decoded summaries, generated token counts, max token settings, and EOS/finish-state fields when available.
- [x] 2.3 Ensure fixture/dry-run paths remain public-safe and do not claim private-adapter evidence.

## 3. Objective Inspection

- [x] 3.1 Add tests for an SFT objective-inspection result that reports prompt-mask and assistant-loss status or a dependency-unavailable state.
- [x] 3.2 Implement the objective-inspection helper/CLI surface without requiring local heavy training.

## 4. Evidence Pack and Reports

- [x] 4.1 Add report/manifest support for train-split overfit diagnostic evidence with `generalization_claim=false` and explicit release/benchmark boundaries.
- [x] 4.2 Generate local fixture-mode diagnostic evidence to validate artifact shape and leak-scan behavior without loading private adapters.
- [x] 4.3 Run focused tests, full tests, lint, type checks, leak scan, `git diff --check`, and `openspec validate --all --strict`.
- [x] 4.4 Generate a concise Chinese Human Brief HTML, sync accepted specs into `openspec/specs/`, and archive the change after validation passes.
