## 1. Freeze audit inputs and RED contracts

- [x] 1.1 Inventory and hash the committed evaluator, prediction/decoding, schema/semantic, ContractCoreV2, projection, public-split audit, internal-core summary, and lockbox aggregate sources without modifying them.
- [x] 1.2 Add RED tests for the audit schema, observed-versus-candidate graph separation, intermediate/leaf authority dimensions, source links, and exact decoding-control terminology.
- [x] 1.3 Add RED tests that fix the renderer population at 247 formal seed rows and separate ITT support, determinism, legacy exact compatibility, supported-only diagnostics, and policy self-consistency, including the rule that 99.77% support is not canonical exact compatibility.
- [x] 1.4 Add RED tests for compiler/model observation units, eligible populations, outcomes, denominators, invalid/unsupported handling, invariants, confounders, negative controls, preset blocked/descriptive statuses, whitelist/denylist, and all false execution/claim flags.

## 2. Implement deterministic read-only audit

- [x] 2.1 Implement an audit-only helper with an explicit source whitelist and lockbox-row denylist that binds required paths/hashes and emits separate observed-current and candidate-only transformation graphs.
- [x] 2.2 Populate intermediate and leaf `value_origin` / `constraint_owner` / `transform` records plus the decoding inventory from source-verified symbols without changing runtime, prompts, schemas, evaluators, predictions, or compilers.
- [x] 2.3 Compute renderer parse/support/determinism/legacy-exact/mismatch/policy-self-consistency counts over exactly 247 formal seed targets; report full-population ITT and secondary supported-only denominators without using SFT, DPO, predictions, or lockbox rows.
- [x] 2.4 Build separate system/compiler and model-learning estimand matrices with matched-arm requirements, confounders, invariants, negative controls, status reasons, and one bounded recommendation.

## 3. Publish public-safe evidence

- [x] 3.1 Generate deterministic `summary.json` and `summary.md` under `reports/public-sample/contract-compiler-v2-causal-boundary/` and verify byte-identical regeneration.
- [x] 3.2 Update evidence-index/current-status navigation with the audit status while preserving raw artifacts as authoritative and avoiding a model-improvement headline.
- [x] 3.3 Generate `docs/human-briefs/2026-07-10-audit-contract-compiler-v2-causal-boundary.html` from the final audit, source hashes, diff, and verification evidence.

## 4. Verify, review, and archive

- [x] 4.1 Assert that public seed/SFT/DPO/manifest, lockbox raw artifacts, prompts, evaluator defaults, prediction artifacts, and model artifacts have no audit-phase mutation.
  - Public seed/SFT/DPO/manifest hashes remained byte-identical after every potentially writing command; no lockbox, prompt/decoding, prediction, model, adapter, checkpoint, or cache path changed. `src/voice2task/evaluation.py` was already modified by the preceding archived repair phase and was not edited by this audit worker.
- [x] 4.2 Run focused audit/renderer/evaluator tests plus read-only public dataset/schema validation, 2100-pair DPO check, deterministic regeneration, and public leak scans; compare protected hashes before and after every command that could write.
  - Focused audit after review Must Fixes: 26 passed. The observed graph covers raw-valid direct, raw-invalid retry, and raw-invalid retry-disabled paths; compiler/model invariant sets are distinct; field authority uses tri-state participation with current constraints separated from hypothetical candidate transforms; exact/descendant denylisted paths, absolute/traversal paths, and both Windows drive forms fail before hash/read while safe near-names remain allowed. Markdown denominators come from audit values. Related renderer/evaluator suite: 116 passed. Public validation: 696 SFT / 2100 DPO, no failures. DPO check: 2100 pairs. Double regeneration: JSON/Markdown byte-identical. Public leak scan: 9 targets / 0 findings.
- [x] 4.3 Run full pytest, `ruff check .`, focused Mypy plus the recorded full-Mypy baseline, `openspec validate --all --strict`, and `git diff --check`.
  - `ruff check .`, focused audit Mypy, OpenSpec strict 12/12, and `git diff --check` passed. Full Mypy reproduced the pre-existing baseline: 39 errors in 5 files while checking 28 source files; the audit module has 0 focused errors.
  - Post-Code-Quality-review rerun: focused audit 26 passed; related renderer/evaluator 116 passed; Ruff, focused audit Mypy, OpenSpec strict 12/12, HTML parse, 9-target public leak scan, deterministic triple-byte comparison, public protected hashes, and `git diff --check` all passed.
  - Final post-review full pytest ran to completion: 713 passed / 4 archive-only active-change guard failures. Exact tests: `tests/test_evidence_surface.py::test_current_truth_surface_checker_passes`; `tests/test_recovered_adapter_challenge_evaluation.py::test_frozen_boundary_passes_with_committed_challenge_and_policy_hashes`; `tests/test_recovered_adapter_challenge_evaluation.py::test_blocked_artifact_contract_for_missing_adapters`; `tests/test_recovered_adapter_challenge_evaluation.py::test_verified_adapters_run_canonical_export_in_disabled_null_and_jsonl_modes`. The first requires zero active changes; the three historical challenge tests reject this audit change solely as `conflicting_active_changes`. Guards remain unchanged and are deferred to 4.5 post-archive closure.
- [x] 4.4 Complete independent read-only spec/code review, resolve every Must Fix without expanding into implementation, and rerun affected validation.
  - Independent Spec Reviewer: `Pass` after audit-only fixes to the observed parse/retry graph, source-verified field authority, and denylist descendant handling.
  - Independent Code Quality Reviewer: `Pass` after audit-only fixes to compiler/model invariant separation, hypothetical authority participation, and Windows/denylisted-file path handling. Final focused audit suite: 26 passed; related renderer/evaluator suite: 116 passed.
- [x] 4.5 Archive only after the Human Brief and validation are current; then run no-active-change truth-surface, strict OpenSpec, leak, and diff checks.
  - Archived to `openspec/changes/archive/2026-07-10-audit-contract-compiler-v2-causal-boundary/` after syncing the new 9-requirement / 21-scenario main capability spec.
  - Post-archive closure: full pytest 717 passed; current truth surface passed; OpenSpec strict 12/12 passed; Ruff, focused audit Mypy, deterministic regeneration, public leak scan, protected public hashes, HTML links, and `git diff --check` passed. Full Mypy remained at the recorded baseline of 39 errors in 5 files while checking 28 source files.
