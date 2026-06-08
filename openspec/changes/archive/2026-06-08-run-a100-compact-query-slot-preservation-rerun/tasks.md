## 1. A100 Preflight

- [x] 1.1 Confirm clean `main`, no unrelated dirty files, no conflicting active OpenSpec changes, and the latest compact query slot preservation archive commit.
- [x] 1.2 Run read-only Explorer over prior A100 rerun commands, private override expectations, evidence shape, tests, validation entry points, and privacy boundaries.
- [x] 1.3 Locate or prepare repo-external private A100 override inputs under the approved private project root without copying private paths or host details into git.
- [x] 1.4 Inspect A100 GPU/process occupancy with `nvidia-smi`, choose a safe idle GPU, and set `CUDA_VISIBLE_DEVICES` explicitly.

## 2. A100 Prediction-Only Rerun

- [x] 2.1 Run one prediction-only train-split rerun using the current compact query slot preservation prompt/data policy and existing private adapter path.
- [x] 2.2 Export sanitized public-sample predictions, prompt snapshot, raw decoded summary, generation trace, prediction metadata, schema guard summary, metrics, and diagnosis artifacts.
- [x] 2.3 Verify `seed-search-weather-aug-1` strict slot-shape outcome and preserve any mismatch honestly without normalization, repair, replacement, or re-score.

## 3. Public Evidence And Human Brief

- [x] 3.1 Import only sanitized public-safe evidence into `reports/public-sample/a100-compact-query-slot-preservation-rerun/`.
- [x] 3.2 Generate report, manifest, metrics summary, diagnosis, leak scans, and `docs/human-briefs/2026-06-08-run-a100-compact-query-slot-preservation-rerun.html`.
- [x] 3.3 Add focused tests for evidence completeness, privacy boundaries, strict metrics, source residual comparison, validation commands, prompt/policy visibility, and no-overclaim wording.

## 4. Validation, Review, Archive

- [x] 4.1 Run focused evidence tests, full `PYTHONPATH=src pytest -q`, `uv run ruff check .`, `uv run mypy src`, public data validation, DPO pair check, leak scans, `git diff --check`, and `openspec validate --all --strict`.
- [x] 4.2 Complete Reviewer pass, fix in-scope Must Fix items only, and rerun required validation.
- [x] 4.3 Archive the OpenSpec change, generate post-archive/final leak scans, rerun post-archive validation, and commit the phase under guarded auto integration.
