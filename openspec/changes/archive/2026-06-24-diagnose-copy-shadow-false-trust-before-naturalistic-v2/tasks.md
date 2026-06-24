## 1. Input Boundary and RED Tests

- [x] 1.1 Add failing tests for diagnosis input boundary validation: challenge hash, policy hash, adapter identity status, prediction/challenge id alignment, sidecar/prediction alignment, audit/gold alignment, prediction invariance, V1 zero-delta, action attested zero, normalized attested zero.
- [x] 1.2 Add failing tests proving `source_attested_exact` is source-only, `trusted_provenance` is a deprecated compatibility alias, `semantic_correctness` is not inferred online, and `execution_eligible` is always false.
- [x] 1.3 Add failing tests for mechanism classification: wrong entity, source-absent substitution, overlong span, underspecified partial span, normalization collision, wrong slot/scope, duplicate disambiguation, technical span attestation failure, and unclassified mismatch.
- [x] 1.4 Add failing tests for normalized-equivalent collision detector cases: `A/B` vs `AB`, `1.2` vs `12`, `C++` vs `C`, `v1.2` vs `v12`, URL punctuation, email punctuation, raw-exact-unique with normalized-equivalent multiple, and fail-closed ambiguous mapping.

## 2. Diagnosis Implementation

- [x] 2.1 Implement a bounded false-trust diagnosis module that reads only committed challenge rows, adapter-evaluation predictions, online sidecars, offline audits, per-scope/per-condition metrics, hook safety audit, and frozen policy v1.
- [x] 2.2 Implement input-boundary checks and blocked decisions `FALSE_TRUST_DIAGNOSIS_BLOCKED_INVALID_INPUT` and `FALSE_TRUST_DIAGNOSIS_INCONSISTENT_ARTIFACTS`.
- [x] 2.3 Implement compatibility mapping from historical `trusted_provenance` to new `source_attested_exact` semantics without overwriting historical artifacts.
- [x] 2.4 Implement deterministic normalized-equivalent collision detection and downgrade raw-exact source-attested collision events to `AMBIGUOUS_NORMALIZATION_COLLISION`.
- [x] 2.5 Implement mechanism classification and case ledger generation for all source-attested-but-gold-mismatch events.
- [x] 2.6 Implement per-scope risk review and policy-v2 proposal status for `search:search_web:query`, `form_fill:fill_form:field`, and `extract:extract_page:target`.

## 3. Reports and Documentation

- [x] 3.1 Generate `reports/public-sample/copy-shadow-false-trust-diagnosis/summary.json`, `summary.md`, `false-trust-case-ledger.jsonl`, `per-scope-risk-review.json`, `normalization-collision-audit.json`, `sidecar-v2-semantics.md`, and `recommended-next-change.md`.
- [x] 3.2 Add `docs/copy-shadow-source-attestation-boundary.md` with source-attestation definition, semantic-correctness boundary, execution eligibility boundary, online/offline audit split, normalization collision, source-absent limitation, partial-span limitation, per-scope risk, policy-v2 proposal boundary, and no-enforcement claims.
- [x] 3.3 Update README, README_en, CONTEXT, and `reports/public-sample/EVIDENCE_INDEX.md` with concise final decision, per-scope proposal, next change, and no-training/no-enforcement/no-model-improvement boundaries.
- [x] 3.4 Add a concise Chinese Human Brief under `docs/human-briefs/2026-06-24-diagnose-copy-shadow-false-trust-before-naturalistic-v2.html`.

## 4. Verification, Review, and Archive Readiness

- [x] 4.1 Verify challenge hash, policy v1 hash, prediction artifact hashes, sidecar deterministic rerun/equivalence, public leak scan, and immutability of challenge rows, gold, policy v1, predictions, sidecars, and audits.
- [x] 4.2 Run `PYTHONPATH=src pytest -q`, `ruff check .`, `OPENSPEC_TELEMETRY=0 openspec validate --all --strict`, `python scripts/check_current_truth_surface.py` after archive, and `git diff --check`.
- [x] 4.3 Run read-only Reviewer subagent over the final diff and fix Must Fix findings only.
- [x] 4.4 Archive the OpenSpec change after all tasks are complete and stop without creating policy v2, naturalistic challenge v2, runtime enforcement, training, data expansion, action enablement, or normalized trusted provenance.
