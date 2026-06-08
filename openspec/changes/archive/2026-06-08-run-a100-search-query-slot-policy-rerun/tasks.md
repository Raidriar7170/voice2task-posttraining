# Tasks

## 1. Scope And Proposal

- [x] 1.1 Confirm this is an A100 prediction-only train-split rerun with no training, no metric relaxation, and no release claim.
- [x] 1.2 Add OpenSpec proposal, design, spec deltas, and tasks.
- [x] 1.3 Validate the OpenSpec change strictly before implementation.

## 2. TDD And Local Preparation

- [x] 2.1 Add failing focused tests for the search-query slot-policy A100 rerun evidence pack, compact target checks, row-level outcomes, source links, leak scans, and strict non-claims.
- [x] 2.2 Run local fixture/pipeline checks needed before remote execution.

## 3. A100 Prediction-Only Rerun

- [x] 3.1 Prepare the A100 runtime in the approved remote workspace using current committed repo state and a repo-external private override.
- [x] 3.2 Inspect GPU/process occupancy, choose a safe idle GPU, set `CUDA_VISIBLE_DEVICES`, and run prediction-only train-split rerun without training.
- [x] 3.3 Copy only sanitized public artifacts into `reports/public-sample/a100-search-query-slot-policy-rerun/`.

## 4. Evidence And Human Brief

- [x] 4.1 Generate metrics, schema guard summary, slot-policy rerun diagnosis, manifest, Markdown report, and leak-scan sidecars from sanitized artifacts.
- [x] 4.2 Generate `docs/human-briefs/2026-06-08-run-a100-search-query-slot-policy-rerun.html`.

## 5. Validation, Review, Archive, Integration

- [x] 5.1 Run focused tests, full pytest, ruff, mypy, public data validation, DPO check, leak scans, `git diff --check`, and OpenSpec strict validation.
- [ ] 5.2 Complete Reviewer pass, fix Must Fix items only, archive the OpenSpec change, generate post-archive/final leak scans, rerun validation, and commit under guarded auto integration.
