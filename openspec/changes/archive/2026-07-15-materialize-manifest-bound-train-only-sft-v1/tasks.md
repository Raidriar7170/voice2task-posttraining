## 1. Contract and red tests

- [x] 1.1 Add builder tests requiring a canonical train-only artifact, manifest path/hash/count binding, ordered-subsequence equality, unchanged provenance, and deterministic bytes
- [x] 1.2 Add validation tests that reject partial binding, absolute/traversal/backslash/outside/symlink paths, missing/hash-drift/noncanonical artifacts, non-train rows, duplicate or blank IDs, count drift, reorder, and row/provenance drift
- [x] 1.3 Run the focused tests before implementation and record the expected feature-missing failures

## 2. Canonical builder and validation

- [x] 2.1 Extend the existing public builder to write the ordered train-only derivative, use repo-relative reference only for canonical formal output and basename elsewhere, and bind final-byte integrity facts without adding a second CLI
- [x] 2.2 Extend dataset validation to require complete binding for `public=True`, reject partial binding in both modes, and retain double-absence compatibility only for explicit `public=False` local/legacy validation
- [x] 2.3 Run focused tests green and confirm existing public/local builder behavior remains compatible

## 3. Formal materialization and historical preservation

- [x] 3.1 Build the formal dataset twice in temporary directories and prove train artifact determinism plus byte-identical mixed SFT/DPO outputs
- [x] 3.2 Materialize only the 282-row train artifact and minimal manifest binding while preserving manifest ID, generated-at, counts, split counts, existing seed, mixed SFT, and DPO bytes
- [x] 3.3 Preserve prior manifest and split-summary bytes in hash-named public snapshots, route frozen historical audits to them, regenerate CURRENT split evidence, and update only the live truth-surface manifest hash
- [x] 3.4 Verify the committed derivative is canonical, train-only, unique-ID, exact ordered-subsequence, public-safe, and correctly hash/count bound

## 4. Review evidence and validation

- [x] 4.1 Generate the Chinese Human Brief with exact no-training/no-prediction/no-evaluation/no-readiness claim boundaries and unchanged clean-evaluation facts
- [x] 4.2 Run focused dataset/validation/history tests, dataset build validation, DPO pair checks, and a public leak/prohibited-claim scan
- [x] 4.3 Run full pytest, Ruff, targeted mypy, strict OpenSpec validation, truth-surface checker, and `git diff --check`
- [x] 4.4 Obtain a read-only Reviewer verdict, fix all in-scope Must Fix findings through the same Worker, and rerun affected verification
- [x] 4.5 Record final `git status --short`, exact validation results, and the protected boundary: no training, prediction, commit, push, archive, or merge

## Verification record

- Focused materializer/history/evidence suite: `192 passed`.
- Full pytest: `1482 passed, 3 failed`; all three failures are the archived recovered-adapter challenge audit correctly rejecting the two active OpenSpec changes. Archive was not authorized, so the lifecycle guard remains unchanged.
- Ruff: pass.
- Targeted mypy: the four other touched Python files pass; `dataset.py` reports its six pre-existing errors at unchanged lines outside this diff.
- Strict OpenSpec validation: `17 passed, 0 failed`.
- Truth-surface checker: exit 1 only because active changes are non-empty (`materialize-manifest-bound-train-only-sft-v1` plus inherited `rerun-real-a100-sft-smoke-after-cli-fix-v1`); no truth drift or allowlist was introduced.
- Dataset validation: `ok=true`, 696 mixed SFT rows, 282 bound train-only rows, and 2100 DPO pairs.
- DPO check: 2100 pairs.
- Public leak/prohibited-claim scan and `git diff --check`: pass.
- Read-only Reviewer final verdict: `Approved`, with no Must Fix or Should Fix.
- Worktree remains uncommitted; no training, prediction, evaluation, GPU work, commit, push, archive, or merge was performed.
