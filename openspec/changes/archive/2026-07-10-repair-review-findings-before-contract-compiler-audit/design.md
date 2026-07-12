## Context

The evaluator currently reaches strict full-contract exact match through Python dictionary equality after strict schema and semantic validation. Because slot values are intentionally open-shaped JSON, Python treats some JSON-distinct values (`true`, `1`, and `1.0`) as equal. Separately, the public evidence navigation predates the completed lockbox evaluation, and the formal public split boundary has accumulated both template reuse and remediation provenance that crosses train/dev/test. The committed 696-row SFT artifact and all historical metrics are evidence and must not be rewritten.

## Goals / Non-Goals

**Goals:**

- Make future strict exact evaluation type-preserving at the JSON value boundary.
- Make final lockbox evidence current and the earlier blocked setup phase explicitly superseded in both index formats.
- Commit a reproducible, public-safe contamination audit for the current formal split and a reusable fail-closed clean-split gate.
- Label current public dev/test evidence as development-only/spent while preserving lockbox-v1 as the frozen one-look evaluation boundary.
- Keep every behavior change covered by a failing regression test before implementation.

**Non-Goals:**

- Do not mutate or resplit the current public seed/SFT/DPO/manifest artifacts.
- Do not recompute historical reports, re-score predictions, or reinterpret old metric values under the repaired evaluator.
- Do not train, predict, use A100, add data, change prompts/decoding, implement Contract Compiler V2, or claim model improvement.
- Do not claim that a lexical/template audit proves semantic independence or natural-ASR provenance.

## Decisions

### 1. Compare the strict JSON domain recursively, not Python containers

Future strict exact checks will use a small recursive comparator after strict parsing and semantic validation. It will accept only JSON-domain values, compare object keys without order sensitivity, preserve array order, distinguish booleans from numbers and integers from floating-point values, and fail closed for non-finite numbers or non-JSON Python objects. Canonical string comparison was considered, but the existing serializer permits non-standard `NaN`/Infinity values by default and can serialize some Python containers that the strict JSON domain should reject.

Historical aggregate artifacts remain frozen. This is a forward evaluator correctness repair, not authorization to re-score prior evidence.

### 2. Treat evidence navigation as a synchronized truth surface

The final lockbox comparison becomes a `CURRENT` index item. The earlier lockbox-lineage guard becomes `SUPERSEDED` and links to the final item instead of being deleted, so its historical blocked state remains auditable. The truth-surface checker and tests will assert the relationship in both JSON and Markdown rather than relying on prose review. The index remains navigation-only: the frozen manifest, final run card, per-arm metrics, and final comparison remain authoritative, and any disagreement must fail closed instead of rewriting those raw artifacts.

### 3. Audit current contamination without rewriting history

A dedicated split-contamination module and CLI will bind the committed public seed, SFT, DPO, and manifest files and emit deterministic JSON and Markdown. Seed/SFT rows drive the overlap analysis; DPO and manifest inputs bind the report to the complete current data boundary. The audit will fail closed on empty, malformed, duplicate-ID, unknown-split, or incomplete train/dev/test inputs while still writing an invalid-input report. It will report at least:

- train-versus-dev/test exact input overlaps;
- full target, `normalized_command`, slots, and structural contract overlaps;
- digit-normalized seed-template signatures spanning splits;
- train rows whose provenance resolves to dev/test source rows, source families, or source split declarations.

The current report will truthfully fail the independent clean-split gate and classify dev/test as `DEVELOPMENT_ONLY_SPENT`. The audit is lexical/provenance evidence only; it does not prove or disprove broader semantic similarity.

### 4. Separate observation from enforcement

The CLI's default audit mode must succeed when it can faithfully report contamination, even when the boundary is not clean. An explicit `--require-clean` mode will exit non-zero for exact-input overlap, a digit-normalized template spanning splits, or train provenance that resolves to dev/test. Complete target, `normalized_command`, slots, and structural-contract overlap remain mandatory diagnostics rather than zero-gate failures: repeated labels and ontology structure can be legitimate across an independent split and cannot by themselves establish leakage. This lets the current historical boundary remain inspectable while forcing future independently claimed boundaries to fail closed on the actual leakage/provenance checks.

### 5. Keep generated evidence reproducible

Machine output will contain a methodology version, all four repo-relative source paths and hashes, input validation, input counts, deterministic sorted findings/counts, the clean-gate result, and claim boundaries. The human summary will be generated from the same result. The truth-surface checker will recompute the complete report from immutable expected source hashes. No wall-clock timestamp, caller working directory, or environment-specific absolute path will affect content.

## Risks / Trade-offs

- [Open-shaped slots can contain non-finite or non-JSON Python values when constructed in memory] → The recursive comparator fails closed outside the finite JSON domain and focused tests cover nested object/array boundaries.
- [Template normalization can over-group or under-group language] → Name the exact digit-normalization heuristic and publish it as diagnostic, not semantic equivalence.
- [A failed current clean gate can be misread as invalidating all historical work] → Preserve historical artifacts and state only that dev/test cannot support an independent blind-generalization claim; lockbox evidence keeps its separate frozen boundary.
- [Adding current evidence while an OpenSpec change is active conflicts with the cleanup checker] → Run the no-active-change truth-surface validation after archiving this repair and before opening the next audit change; validate the next change with OpenSpec's strict validator.

## Migration Plan

1. Add RED tests for JSON-type strictness, index synchronization, contamination reporting, clean-gate failure/success, and public documentation wording.
2. Implement the evaluator comparison, audit module/CLI, truth-surface guard, evidence artifacts, and documentation changes.
3. Run focused validation, review the diff, resolve Must Fix findings, and rerun affected plus full validation.
4. Generate the Chinese Human Brief from the final diff and verification evidence, then archive the repair change.
5. With no active change, run strict OpenSpec and cleanup truth-surface validation.
6. Open `audit-contract-compiler-v2-causal-boundary` as an artifact-only proposal/design/spec/tasks phase.

Rollback is a normal branch revert. Historical data and metrics require no migration because they are not modified.

## Open Questions

None for this bounded repair. A future clean split's construction policy and any new training/evaluation execution belong to separate reviewed changes.
