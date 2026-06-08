## 1. Preflight And Remote Safety

- [x] 1.1 Inspect current repo status, active OpenSpec state, prior A100 first-pass evidence, and local fence-suppression evidence.
- [x] 1.2 Prepare a repo-external private A100 override under the approved private project root with explicit prediction opt-in and current code path.
- [x] 1.3 Check A100 GPU/process occupancy, choose a safe idle GPU, and avoid interrupting other users.
- [x] 1.4 Validate the OpenSpec change strictly before remote execution.

## 2. A100 Prediction-Only Rerun

- [x] 2.1 Run prediction-only train-split export with the existing private adapter and current Markdown fence suppression decoding policy.
- [x] 2.2 Keep remote outputs, logs, adapters, caches, private configs, host details, SSH details, tokens, and private paths outside git.
- [x] 2.3 Bring back only sanitized public-sample predictions, metadata, prompt snapshot, raw decoded summary, generation trace, and derived reports.

## 3. Evidence, Tests, And Human Brief

- [x] 3.1 Generate `reports/public-sample/a100-first-pass-fence-suppression-rerun/` with manifest, metrics, schema guard summary, rerun diagnosis, report, and leak scans.
- [x] 3.2 Add focused tests for wrapper counts, strict metric boundaries, suppression metadata presence, privacy boundaries, and no overclaim.
- [x] 3.3 Generate `docs/human-briefs/2026-06-08-run-a100-first-pass-fence-suppression-rerun.html`.

## 4. Validation, Review, Archive, Integration

- [x] 4.1 Run focused tests, full `PYTHONPATH=src pytest -q`, `uv run ruff check .`, `uv run mypy src`, public data validation, DPO pair check, public leak scans, `git diff --check`, and `openspec validate --all --strict`.
- [x] 4.2 Complete Reviewer pass, fix in-scope Must Fix items only, and rerun required validation.
- [x] 4.3 Archive the OpenSpec change, rerun post-archive validation, and commit the phase under guarded auto integration.
