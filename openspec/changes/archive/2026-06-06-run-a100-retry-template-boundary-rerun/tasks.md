## 1. Discovery And TDD

- [x] 1.1 Inspect the previous A100 retry JSON-only rerun artifacts, local retry template boundary evidence, private prediction CLI sidecars, and validation entry points.
- [x] 1.2 Add failing focused tests for the A100 retry template rerun evidence pack, manifest/diagnosis claims, source links, retry-template metadata, leak scans, and strict non-claim boundaries.

## 2. A100 Prediction-Only Rerun

- [x] 2.1 Prepare the A100 runtime under an approved private project directory, using the current committed repo state and a repo-external private prediction override.
- [x] 2.2 Inspect GPU/process occupancy, select an idle GPU safely, set `CUDA_VISIBLE_DEVICES` explicitly, and run the prediction-only train-split rerun without training or parser/evaluator changes.
- [x] 2.3 Copy only sanitized public artifacts into `reports/public-sample/a100-retry-template-boundary-rerun/`.

## 3. Evidence And Human Brief

- [x] 3.1 Generate metrics, schema guard summary, retry-template boundary diagnosis, manifest, Markdown report, and leak-scan sidecars from sanitized artifacts.
- [x] 3.2 Generate `docs/human-briefs/2026-06-06-run-a100-retry-template-boundary-rerun.html` with observed results, validation, source links, limitations, non-claims, and recommended next step.

## 4. Validation And Review

- [x] 4.1 Run focused tests, full test suite, lint/type checks, public data validation, DPO pair checks, public-leak scans, `git diff --check`, and `openspec validate --all --strict`.
- [x] 4.2 Complete Reviewer pass, fix Must Fix items only, archive the OpenSpec change, generate post-archive/final leak-scan sidecars, rerun validation, and commit the phase under guarded auto integration.
