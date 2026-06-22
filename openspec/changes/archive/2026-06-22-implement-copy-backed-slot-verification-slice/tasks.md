## 1. Boundary And Tests

- [x] 1.1 Confirm the required recovered raw inputs, hybrid design artifacts, internal ContractCoreV2 evidence, V1 schema/evaluator evidence, and formal public sample manifest are present and within the allowed boundary.
- [x] 1.2 Add focused failing tests for exact unique source spans, duplicate-span fail-closed behavior, bounded normalized matching with offset mapping, disabled action scope, sidecar-only provenance, and report decision gates.

## 2. Verifier Implementation

- [x] 2.1 Implement `src/voice2task/copy_backed_slot_verification.py` with system-owned source-span verification statuses, provenance, Unicode character offsets, source text hashing, and fail-closed behavior.
- [x] 2.2 Implement a read-only report script that builds the task-scoped policy, verifies gold and Control/Treatment predictions, separates provenance from correctness, preserves historical metric names, and rejects invalid boundaries with `COPY_SLICE_BLOCKED_INVALID_INPUT`.
- [x] 2.3 Generate `reports/public-sample/copy-backed-slot-verification-slice/summary.md`, `summary.json`, `task-scoped-policy.json`, `verification-audit.json`, `recommended-next-change.md`, and optional `verification-sidecars.jsonl`.

## 3. Truth Surface And Archive

- [x] 3.1 Add concise updates to `docs/copy-backed-slot-verification.md`, `CONTEXT.md`, `README.md`, `README_en.md`, `reports/public-sample/EVIDENCE_INDEX.md`, and `reports/public-sample/evidence-index.json`.
- [x] 3.2 Archive the OpenSpec change, sync the long-lived `copy-backed-slot-verification` spec, and generate a concise Chinese Human Brief.

## 4. Verification

- [x] 4.1 Run focused tests and full validation: `PYTHONPATH=src pytest -q`, `PYTHONPATH=src ruff check src tests scripts/run_copy_backed_slot_verification_slice.py`, `OPENSPEC_TELEMETRY=0 openspec validate --all --strict`, `python scripts/check_current_truth_surface.py`, `git diff --check`, and public leak scan.
- [x] 4.2 Review the final diff for scope boundaries and stop without training, prediction rerun, evaluator changes, action enablement, runtime integration, or GitHub push unless separately requested.
