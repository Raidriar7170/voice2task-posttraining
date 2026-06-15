## Context

`reports/public-sample/form-fill-remediation-plan/form_fill_remediation_plan.json` is the current source of truth for the selected `form_fill` remediation target. It is already public-safe and plan-only: 29 residual rows, 49 residual fields, and three buckets:

- `confirmation_marker_missing_or_reordered`
- `field_name_specificity_drift`
- `clarify_boundary_confusion`

The next useful artifact is not more training data yet. It is a reviewable design that tells a human what kinds of examples or prompt-policy wording would address each bucket while preserving the formal public held-out boundary.

## Goals / Non-Goals

**Goals:**
- Generate a deterministic `form_fill` remediation case-design object from the existing plan artifact.
- Publish public-safe JSON, Markdown, manifest, and Human Brief evidence.
- Include candidate case groups and prompt/policy guidance for each remediation bucket.
- Fail closed when the source artifact is not the expected `form_fill` plan-only diagnosis.
- Keep strict `contract_exact_match` and strict `slot_f1` as the authoritative metrics.

**Non-Goals:**
- Do not write or modify `seed_traces.jsonl`, public-sample split files, SFT rows, DPO pairs, or held-out gold labels.
- Do not run SFT, DPO, prediction, A100 jobs, or live-browser smoke.
- Do not change evaluator scoring or promote `slot_f1_soft` to a primary metric.
- Do not claim checkpoint release, adapter release, production readiness, or live-browser benchmark improvement.

## Decisions

1. **Use the existing plan artifact as the only input.**
   - Rationale: the prior phase already performed residual grouping and public sanitization. Re-reading raw predictions would expand scope and increase leak risk.
   - Alternative considered: regenerate residuals from predictions. Rejected because this phase is case design, not diagnosis.

2. **Represent guidance and cases separately.**
   - Rationale: prompt/policy guidance captures the intended contract rule, while candidate cases capture reviewable example shapes for a later materialization phase.
   - Alternative considered: directly emit seed rows. Rejected because materialization needs a separate boundary and user review.

3. **Keep exactly three design groups mapped to the three plan buckets.**
   - Rationale: the buckets are the stable decision units from the previous diagnosis, and they map cleanly to future prompt/data review.
   - Alternative considered: generate one case per residual row. Rejected as too noisy for review and likely to overfit to row IDs.

4. **Expose this as a report/CLI pattern matching prior diagnostic phases.**
   - Rationale: existing tests and CLI conventions already verify public-safety and claim boundaries.
   - Alternative considered: hand-write a Markdown report only. Rejected because machine-readable JSON is needed for tests and later materialization.

## Risks / Trade-offs

- [Risk] The generated cases could be mistaken for materialized training data. → Mitigation: manifest and tests assert `new_data_generated=false`, `public_sample_modified=false`, `training_run=false`, and `a100_job=false`.
- [Risk] Case examples can overfit to current held-out row wording. → Mitigation: each group proposes bucket-level example shapes and states that materialization requires review.
- [Risk] `slot_f1_soft` could be used as proof of recovery. → Mitigation: report and tests keep soft metrics diagnostic-only and strict metrics primary.
- [Risk] Public report could leak private paths or raw artifacts. → Mitigation: use existing sanitizer and leak-scan tests over committed artifacts and Human Brief.

## Migration Plan

1. Add the case-design generator, writer, CLI, and tests.
2. Generate committed public-safe evidence under `reports/public-sample/form-fill-remediation-case-design/`.
3. Add a Human Brief under `docs/human-briefs/`.
4. Validate with focused tests, full tests, ruff, OpenSpec strict validation, leak scan, and `git diff --check`.

Rollback is deleting the new generator/CLI/tests/report artifacts and reverting this OpenSpec archive. No existing data or model artifacts are changed.

## Open Questions

- Which reviewed cases, if any, should become a later independent candidate dataset? That is intentionally deferred to a separate materialization phase.
- Whether prompt-only changes are enough or targeted SFT is needed remains unknown until a later reviewed materialization/evaluation phase.
