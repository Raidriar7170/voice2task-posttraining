## 1. Boundary And Tests

- [x] 1.1 Confirm the previous copy-backed verification slice, recovered raw inputs, V1 evaluator evidence, and truth-surface boundaries are valid for shadow-mode integration.
- [x] 1.2 Add focused failing tests for one-sidecar-per-prediction attachment, nested slot diagnostics, action disabled behavior, non-mutation/raw-hash preservation, V1 zero delta, and shadow decision gates.

## 2. Shadow Mode Implementation

- [x] 2.1 Implement `scripts/run_copy_backed_verification_shadow_mode.py` using the existing verifier and task-scoped policy without widening normalization or enabled slots.
- [x] 2.2 Generate `reports/public-sample/copy-backed-verification-shadow-mode/summary.md`, `summary.json`, `shadow-sidecars.jsonl`, `shadow-compatibility.json`, and `recommended-next-change.md`.
- [x] 2.3 Ensure invalid boundaries write `blocked.json` with `SHADOW_MODE_BLOCKED_INVALID_INPUT` and no success artifacts.

## 3. Truth Surface And Archive

- [x] 3.1 Add concise updates to `docs/copy-backed-verification-shadow-mode.md`, `CONTEXT.md`, `README.md`, `README_en.md`, `reports/public-sample/EVIDENCE_INDEX.md`, and `reports/public-sample/evidence-index.json`.
- [x] 3.2 Archive the OpenSpec change, sync the long-lived `copy-backed-verification-shadow-mode` spec, and generate a concise Chinese Human Brief.

## 4. Verification

- [x] 4.1 Run focused tests and full validation: `PYTHONPATH=src pytest -q`, `PYTHONPATH=src ruff check src tests scripts/run_copy_backed_verification_shadow_mode.py`, `OPENSPEC_TELEMETRY=0 openspec validate --all --strict`, `python scripts/check_current_truth_surface.py`, `git diff --check`, JSON validation, and public leak scan.
- [x] 4.2 Review the final diff for scope boundaries and stop without runtime enforcement, action enablement, training, prediction repair, evaluator changes, or GitHub push unless separately requested.
