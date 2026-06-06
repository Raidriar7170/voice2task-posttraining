## 1. A100 Preflight

- [x] 1.1 Identify the prior private-adapter prediction command/template and local retry-boundary hardening evidence to reuse.
- [x] 1.2 Check A100 access, GPU/process occupancy, approved private output root, private override availability, and selected `CUDA_VISIBLE_DEVICES` before launching GPU work.

## 2. Prediction-Only Rerun

- [x] 2.1 Run a train-split private-adapter prediction-only export with schema retry enabled, stricter retry JSON-only prompt policy, and no parser/evaluator/repair behavior changes.
- [x] 2.2 Collect sanitized predictions, metrics, prompt snapshot, raw decoded summary, generation trace, prediction metadata, and leak-scan sidecars into a public-safe evidence directory.

## 3. Retry-Boundary Diagnosis

- [x] 3.1 Generate schema guard and retry-boundary diagnosis artifacts summarizing raw/retry parse status, wrapper status, strict final metrics, retry prompt constraints, and unproven claims.
- [x] 3.2 Publish a manifest and report that compare only to the bounded prior A100 stop-boundary rerun and local retry JSON-only hardening evidence.

## 4. Human Brief And Tests

- [x] 4.1 Add or update tests asserting the A100 retry-boundary rerun evidence pack is public-safe, bounded, and preserves strict metrics and non-claims.
- [x] 4.2 Generate a concise Chinese Human Brief with verification results, evidence links, limitations, and recommended next step.

## 5. Validation And Closeout

- [x] 5.1 Run focused tests, full test suite, lint/type checks, public data validation, DPO pair checks, public-leak scans, `git diff --check`, and `openspec validate --all --strict`.
- [x] 5.2 Complete Reviewer pass, fix Must Fix items only, archive the OpenSpec change, generate post-archive/final leak-scan sidecars, rerun validation, and commit the phase under guarded auto integration.
