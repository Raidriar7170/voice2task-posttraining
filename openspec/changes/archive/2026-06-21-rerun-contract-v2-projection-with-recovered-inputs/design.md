## Context

The historical `reports/public-sample/contract-v2-projection/` evidence is a
blocked artifact: it intentionally did not compute metrics because current
step-matched raw prediction contracts were missing. The follow-up recovery
change produced public-safe raw inputs under
`reports/public-sample/step-matched-canonical-slot-ablation/raw-inputs/`, with
`projection_inputs_ready=true` and metric reproduction recorded as
`reproduced`. This rerun uses that recovered artifact set as the only source of
model outputs.

## Goals / Non-Goals

**Goals:**

- Verify the recovered raw-input boundary before any projection metric is
  emitted.
- Project only parsed `prediction_contract` and `gold_contract` objects, never
  reconstructed `raw_model_output` text.
- Preserve the existing V1 schema, validation, strict evaluator, and layered
  metric meanings.
- Compute separate L0, L1, L2, and L3 projection metrics for Control and
  Treatment dev/test splits.
- Classify strict failures into bounded derived-field and core-failure
  categories.
- Generate all required rerun evidence in
  `reports/public-sample/contract-v2-projection/rerun-with-recovered-inputs/`.
- Update truth surfaces and a short Human Brief with non-claims and next-step
  boundaries.

**Non-Goals:**

- No A100, SSH, GPU work, SFT, DPO, GRPO, prediction rerun, data expansion,
  split change, gold change, prompt change, evaluator relaxation, LLM judge,
  semantic-equivalence scoring, prediction repair, or model improvement claim.
- No formal production Contract V2 implementation, runtime consumer change,
  V1 schema change, SFT/DPO formatting change, adapter/checkpoint release, or
  Voice-to-Browser Agent integration.
- No automatic follow-on change after the evidence and decision are written.

## Decisions

### Decision 1: Treat `reproduced` as the recovered metric pass state

The recovery artifact records `metric_reproduction_status="reproduced"` rather
than `passed`. The rerun boundary accepts that exact status as the already
verified pass state for recovered metrics and records the normalization in
`source-boundary.json`; it does not edit or relabel the recovery artifact.

Rationale: failing the rerun because of a different success string would
discard valid recovered evidence. Editing the previous artifact would be worse,
because it would rewrite historical evidence outside this bounded change.

### Decision 2: Keep V2 Core pure and field-limited

V2 Core contains exactly `task_type`, `route`, `safety`,
`confirmation_required`, and `slots`. Projection copies these fields from a
valid V1 contract and rejects any extra field.

Rationale: the phase measures whether derived fields explain strict failures.
It must not introduce `allowed_actions`, `success_criteria`, `policy_tags`,
`runtime_hints`, or other schema ideas that belong to a later formal design.

### Decision 3: Use parsed contracts, not raw decoded text

The report command reads `prediction_contract` and `gold_contract` from the
recovered JSONL rows. `raw_model_output` is retained only as provenance because
it may be canonical JSON reconstructed from existing sidecars, not token-level
decoder text.

Rationale: projection is a contract-structure evaluation. Treating
`raw_model_output` as authoritative would mix provenance reconstruction with
metric semantics.

### Decision 4: Preserve V1 metrics as L0 and name projection metrics separately

L0 carries V1 strict and executable metrics using existing evaluator code.
L1/L2/L3 are named `v1_without_normalized_command_exact`,
`v2_core_exact_match`, and V2 envelope metrics. They never replace or rename
`contract_exact_match_strict`.

Rationale: this is a counterfactual schema view, not a new definition of model
quality.

### Decision 5: Renderer fails closed and reads only core fields

The normalized-command renderer uses bounded deterministic templates for the
current search, navigate, form_fill, extract, clarify, and blocked families.
Unsupported shapes return a structured unsupported result.

Rationale: the renderer tests postprocessor feasibility without LLM generation,
fuzzy equivalence, slot rewriting, or value merging.

## Risks / Trade-offs

- Boundary mismatch or stale inputs -> write `PROJECTION_INVALID_INPUT_BOUNDARY`
  / `PROJECTION_INVALID_OR_BLOCKED` evidence and stop.
- Exact improves while executable pass does not -> report schema-burden relief
  only, not semantic improvement.
- Renderer coverage hides core slot failures -> publish coverage, unsupported
  reasons, and residual core-failure counts separately.
- Multiple active OpenSpec changes touch projection language -> this rerun uses
  a distinct capability id and output directory to avoid rewriting the prior
  blocked evidence.

## Migration Plan

There is no runtime migration. Rollback is removal of the rerun module/script
changes, tests, the rerun evidence directory, and this OpenSpec change.

## Open Questions

- None for implementation. Any decision to formally implement Contract V2 or
  adjust the renderer policy is a later bounded change.
