## 1. Reproduce the Real CLI Failure

- [x] 1.1 Add an SFT CLI regression that emits the two observed Trainer mapping lines before a completed result, then prove the unmodified CLI stdout is not one JSON document
- [x] 1.2 Add noisy runtime-exception and DPO dispatch regressions that require one result JSON on stdout, non-zero/zero typed exits, and only prefixed non-result diagnostics on stderr

## 2. Implement the CLI Output Boundary

- [x] 2.1 Add a line-aware streaming stderr diagnostic adapter and redirect all backend Python stdout at the unified CLI dispatch boundary
- [x] 2.2 Keep final success/failure JSON rendering outside the redirect context and preserve the existing public allowlist and exit-code mapping
- [x] 2.3 Run the focused CLI tests through RED/GREEN and the related A100/preflight regression modules without model downloads, GPU access, or training
  - RED: focused noisy SFT success, noisy exception, and mock-only DPO dispatch failed `3/3` because backend output contaminated stdout.
  - GREEN: the focused tests passed `3/3`; full review-hardening plus private-preflight regression passed `154/154`.

## 3. Audit and Documentation

- [x] 3.1 Generate `docs/human-briefs/2026-07-15-fix-real-sft-cli-single-json-v1.html` with the observed failure, bounded fix, validation evidence, and explicit no-rerun/no-stage-two boundary
- [x] 3.2 Run an independent read-only review and resolve every Must Fix while preserving clean-evaluation truth and the prior runtime-postcondition-failed status
  - Independent verdict: Pass; Must Fix none, Should Fix none, Re-plan not needed. The review also exercised a real `tqdm(..., file=sys.stdout)` compatibility path without training.

## 4. Pre-Archive Verification

- [x] 4.1 Run focused and full `PYTHONPATH=src pytest -q`, `PYTHONPATH=src ruff check .`, targeted Mypy for touched training files, `OPENSPEC_TELEMETRY=0 openspec validate --all --strict`, and `git diff --check`; record any active-change-only lifecycle failure without adding an allowlist
  - Focused CLI regression: 154 passed. Full pre-archive suite: 1450 passed and 4 active-change-only lifecycle/frozen-boundary guard failures; no allowlist was added. Ruff, strict OpenSpec 16/16, and diff check passed. Targeted Mypy has no touched-file diagnostic and only the two recorded imported-module baseline diagnostics.
- [x] 4.2 Run the read-only formal public-data/schema and DPO checks: `PYTHONPATH=src python -m voice2task.cli.data validate --sft data/public-samples/sft_public_sample.jsonl --dpo data/public-samples/dpo_public_sample.jsonl --manifest data/public-samples/manifest_public_sample.json --public`, `PYTHONPATH=src python -m voice2task.cli.data dpo-check --dpo data/public-samples/dpo_public_sample.jsonl`, and `PYTHONPATH=src pytest -q tests/test_dataset_builder.py tests/test_schemas.py tests/test_dpo_validation.py tests/test_evaluator_reports.py`
  - Formal validation passed with 696 SFT rows and 2100 DPO pairs; DPO check read 2100 pairs; the focused dataset/schema/DPO/evaluator suite passed 88 tests.
- [x] 4.3 Run a public leak scan over all changed public artifacts and confirm no private config, runtime path, host fact, log, adapter, cache, or remote connection detail is tracked
  - The explicit changed-artifact scan returned zero findings; scoped tracked/status checks for `data/local-private` returned empty.

## 5. Lifecycle Closeout

- [x] 5.1 Sync the delta into `supervised-contract-tuning`, archive the change, confirm active changes are zero, then rerun full pytest, Ruff, targeted Mypy, strict OpenSpec validation, `PYTHONPATH=src python scripts/check_current_truth_surface.py`, public leak/ignore/status guards, and `git diff --check`
  - The complete delta requirement was synchronized byte-for-byte and the change was archived at `openspec/changes/archive/2026-07-15-fix-real-sft-cli-single-json-v1`; active changes are zero.
  - Post-archive full pytest passed 1454 tests. Ruff, strict OpenSpec 15/15, current truth-surface, five Human Brief links, public leak scan, private ignore/untracked/status guards, and `git diff --check` passed.
  - Targeted Mypy has zero diagnostics in the touched training files and only the two recorded imported-module baseline diagnostics. Direct Stop-hook probes returned exit code 0 for both valid input and the fatal-parse catch path.
  - No second real smoke, full training, DPO, GRPO, prediction, evaluation, lockbox access, GPU execution, or model-improvement claim occurred.
