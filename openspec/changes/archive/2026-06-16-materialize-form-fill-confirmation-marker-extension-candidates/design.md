## Context

The archived `extend-form-fill-confirmation-marker-coverage` phase produced a public-safe design artifact with 12 source-family-level confirmation-marker cases:

- Source artifact: `reports/public-sample/form-fill-confirmation-marker-coverage-extension/form_fill_confirmation_marker_coverage_extension.json`
- Evidence kind: `form_fill_confirmation_marker_coverage_extension_design`
- Proposed cases: 12
- Derived field-label cases: 3
- Family-level cases without derivable field labels: 9
- Recommended next step: `materialize_bounded_confirmation_marker_extension_candidates_in_later_phase`

Existing candidate materializers already provide the desired boundary pattern: standalone candidate seed rows, candidate SFT rows, JSON/Markdown/manifest evidence, and explicit `formal_public_sample_modified=false` style claims. This phase reuses that pattern for confirmation-marker extension cases.

## Goals / Non-Goals

**Goals:**

- Generate standalone candidate seed rows from the reviewed confirmation-marker extension design.
- Generate candidate SFT rows from those seeds without creating DPO pairs.
- Preserve source design provenance, source family ids, source bucket, derivation status, and expected confirmation marker.
- Publish public-safe evidence under `reports/public-sample/form-fill-confirmation-marker-extension-materialized-candidates/`.
- Keep candidate rows separate from `data/public-samples/seed_traces.jsonl` and the formal public sample manifest.

**Non-Goals:**

- No formal public sample merge.
- No public sample split rebuild.
- No prompt change, evaluator relaxation, prediction repair, prediction run, A100 job, SFT/DPO/GRPO training, checkpoint release, or adapter release.
- No held-out recovery, model recovery, production readiness, private-corpus generalization, public full-corpus release, or live-browser benchmark claim.
- No attempt to invent field labels for cases whose source design marks field labels as not derivable from committed artifacts.

## Decisions

- Materialize one seed per reviewed design case.
  - Rationale: the source design already chose a source-family-level coverage unit, and one seed per case keeps the phase auditable.
  - Alternative considered: expand one row per original residual incidence. Rejected because the committed source artifact does not contain raw residual text for all 27 incidences and this phase must stay public-safe.

- For derived field-label cases, use `task_type="form_fill"`, `route="fill_form"`, `confirmation_required=true`, `slots.field=<derived label>`, and `normalized_command="填写<field>并确认"`.
  - Rationale: these cases contain field labels derived from committed coverage examples and match the existing form-fill remediation contract policy.
  - Alternative considered: preserve the exact design pattern string as free text. Rejected because a schema-valid Browser Task Contract still needs a structured slot.

- For non-derivable source-family cases, materialize family-level confirmation targets with stable public-safe field labels derived from the source family id.
  - Rationale: the source design intentionally did not expose raw private field text for these families. A deterministic family-level placeholder keeps the candidate public-safe while still teaching the confirmation-marker boundary.
  - Alternative considered: skip non-derivable cases. Rejected because that would leave the largest coverage gap unmaterialized and contradict the design summary.

- Keep the output candidate-only.
  - Rationale: the project evidence ladder requires a separate preview/merge/evaluation phase before any formal public sample mutation or model claim.
  - Alternative considered: immediately append rows to `data/public-samples/seed_traces.jsonl`. Rejected because that would combine materialization and merge decisions in one phase.

## Risks / Trade-offs

- [Risk] Family-level placeholder field labels may be mistaken for real held-out field labels. -> Mitigation: provenance records `field_label_derivation_status`, and reports state that non-derivable labels are public-safe candidate labels, not recovered gold labels.
- [Risk] Candidate-only materialization may be mistaken for model improvement. -> Mitigation: execution scope and claims explicitly state no prediction, training, or held-out recovery occurred.
- [Risk] Future merge may need a separate integration check before touching formal public files. -> Mitigation: manifest recommends a later preview/merge OpenSpec phase instead of directly merging.
