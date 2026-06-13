## 1. Local Contract and Configs

- [x] 1.1 Add focused tests for current-manifest tiny-adapter held-out prediction config templates and public-safe boundaries.
- [x] 1.2 Add public-safe `dev` and `test` prediction config templates for `public-sample-20260613T072200Z`.
- [x] 1.3 Update OpenSpec deltas for prediction-only held-out execution and evidence publication.

## 2. A100 Prediction-Only Diagnostic

- [x] 2.1 Sync code, configs, and current public-sample data to the approved private A100 project root.
- [x] 2.2 Inspect GPU/process occupancy and choose an idle GPU explicitly.
- [x] 2.3 Run prediction-only exports for current manifest `dev` and `test`, or write a public-safe blocked record if execution is unsafe.

## 3. Evidence and Closeout

- [x] 3.1 Import only sanitized evidence under `reports/public-sample/current-tiny-adapter-heldout-prediction/`.
- [x] 3.2 Generate a concise Chinese Human Brief HTML with bounded claims.
- [x] 3.3 Run focused pytest, OpenSpec validation, leak scans, and `git diff --check`; then archive the change if complete.
