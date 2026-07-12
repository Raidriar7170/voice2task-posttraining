## 1. Lock RED regressions

- [x] 1.1 Add evaluator regressions that distinguish JSON boolean, integer, and floating-point slot values while accepting key-order-only differences, and run them to confirm RED.
- [x] 1.2 Add evidence-index/truth-surface regressions for current final lockbox evidence and superseded lineage-guard history, and run them to confirm RED.
- [x] 1.3 Add split-audit and CLI regressions for contaminated and clean fixtures plus current committed counts, and run them to confirm RED.

## 2. Implement bounded repairs

- [x] 2.1 Replace Python container equality with a fail-closed recursive JSON-domain type-strict comparison in future evaluator execution without re-scoring historical artifacts.
- [x] 2.2 Implement deterministic split-contamination audit/report generation and explicit fail-closed clean enforcement without modifying formal public data.
- [x] 2.3 Reconcile JSON/Markdown evidence indexes and strengthen the truth-surface checker against final-lockbox status drift.
- [x] 2.4 Update README, README_en, CONTEXT, and current-status wording for type-strict exact semantics and development-only/spent public dev/test evidence.

## 3. Publish split-audit evidence

- [x] 3.1 Generate committed public-safe split-contamination JSON/Markdown artifacts from the current formal seed and SFT files and verify deterministic regeneration.

## 4. Validate and review

- [x] 4.1 Run focused evaluator, dataset-builder/split-audit, evidence-surface, project-surface, schema-metric, and DPO validation tests.
- [x] 4.2 Run `voice2task-data validate`, `voice2task-data dpo-check`, public leak scans, full pytest, `ruff check .`, `mypy src`, `openspec validate --all --strict`, and `git diff --check`; record any pre-existing limitation exactly.
  - Standard focused invocation `PYTHONPATH=src pytest -q ...`: 104 passed, with only the active-change cleanup test intentionally deselected.
  - Standard full invocation `PYTHONPATH=src pytest -q`: 687 passed / 4 failed while this change is active; all four failures are existing active-OpenSpec cleanup/frozen-boundary guards and require post-archive rerun.
  - Full `mypy src` remains at the pre-existing baseline of 39 errors in 5 files; the changed evaluator and new split-integrity module pass focused mypy.
  - Data validation, 2100-pair DPO check, deterministic JSON/Markdown regeneration, public leak scan, full ruff, OpenSpec strict validation, and `git diff --check` pass.
- [x] 4.3 Complete read-only code-quality review, resolve every Must Fix finding, and rerun affected plus full validation.

## 5. Brief, archive, and post-archive checks

- [x] 5.1 Generate `docs/human-briefs/2026-07-10-repair-review-findings-before-contract-compiler-audit.html` from the final change artifacts, diff, and verification evidence.
- [x] 5.2 Mark tasks complete and archive the repair change.
- [x] 5.3 With no active change, run `openspec validate --all --strict`, `python scripts/check_current_truth_surface.py`, public leak scans, and `git diff --check` before opening the next audit phase.
  - Post-archive full pytest: 691 passed.
  - Post-archive truth-surface check, OpenSpec strict 11/11, Ruff, public leak scan, and diff check passed after removing two spec-sync trailing blank lines.
  - Full `mypy src` remains the pre-existing 39 errors in 5 files; no new errors were introduced in the changed evaluator or split-integrity module.
