## Context

The current V1 contract asks the model to emit core executable fields and
derived/display metadata in the same JSON object. Recent evidence shows the
pipeline can emit schema-valid JSON, but strict full-contract exact match and
strict slot metrics remain weak. The latest step-matched canonical-slot SFT
ablation did not justify more small candidate loops, DPO, or immediate
training.

This phase is design plus offline evaluation only. It uses the latest committed
step-matched control/treatment dev/test predictions and gold contracts, aligns
them by stable sample id, projects both gold and prediction contracts to
smaller deterministic views, and measures how much strict failure is explained
by derived fields versus core slot/task/route/safety/confirmation errors.

## Goals / Non-Goals

**Goals:**

- Repair README, README_en, and CONTEXT current truth surfaces before analysis.
- Discover the latest step-matched ablation artifacts from committed files.
- Verify dev/test sample id parity, gold contract parity, prediction/gold
  alignment, V1 schema source from code, and local-only execution boundaries.
- Add deterministic, pure functions:
  - `project_v1_to_v2_core(contract)`;
  - `validate_v2_core(core_contract)`;
  - `canonical_v2_core_json(core_contract)`;
  - `build_v2_envelope(core_contract)`;
  - `deterministic_normalized_command_renderer(core_contract)`.
- Compute L0/L1/L2/L3 projection ladder metrics, field contribution analysis,
  task/family deltas, bootstrap deltas, renderer coverage, and a bounded
  decision label.
- Publish public-safe machine-readable and human-readable artifacts under
  `reports/public-sample/contract-v2-projection/`.

**Non-Goals:**

- No A100, SSH, GPU job, SFT, DPO, GRPO, prediction rerun, dataset merge,
  split change, LoRA tuning, base-model change, prompt change, evaluator
  relaxation, LLM judge, prediction repair, or semantic-equivalence scoring.
- No V1 production schema change, runtime consumer change, SFT/DPO formatting
  change, formal Contract V2 production rollout, adapter/checkpoint release, or
  Voice-to-Browser Agent integration.
- No model improvement, held-out recovery, production readiness, safety
  readiness, live-browser benchmark, public full-corpus, checkpoint release, or
  adapter release claim.
- No automatic next change after this phase, even if the recommendation names
  one.

## Decisions

### Decision 1: Keep V2 Core experimental and pure

The projection module returns plain dictionaries and validates them without
network, model, runtime, or A100 dependencies. V2 Core contains only
`task_type`, `route`, `safety.allow`, `safety.reason`,
`confirmation_required`, and `slots`.

Rationale: this isolates the architecture question without changing the
production V1 schema or evaluator. Alternatives such as modifying
`BrowserTaskContract` or adding runtime postprocessors would widen this phase
into implementation and production integration.

### Decision 2: Treat `normalized_command` as display/diagnostic in projection

The deterministic renderer builds a display command from task type, route, and
canonical slots when a bounded template is available. Unsupported cases return
a structured unsupported result instead of free-form text.

Rationale: the phase tests whether a deterministic postprocessor could remove a
derived-field consistency burden. It must not read predicted
`normalized_command`, infer semantic equivalence, or alter slots. Alternatives
such as LLM judging or fuzzy substitution would relax the metric and obscure the
strict failure source.

### Decision 3: Preserve V1 strict metrics as L0

L0 reads existing V1 strict/executable metrics unchanged. L1/L2/L3 are new
projection metrics and must never overwrite or rename V1 strict exact.

Rationale: the project needs counterfactual evidence, not a redefinition of
success. Existing evaluator and layered evaluator semantics stay authoritative.

### Decision 4: Fail closed on missing or unalignable inputs

The report command must create a blocked artifact and stop if required source
artifacts are absent, dev/test sample IDs differ, gold contracts differ, or
predictions cannot be aligned by stable sample id.

Rationale: the phase is only credible if it is grounded in current committed
Control/Treatment evidence. Using old adapter predictions or inferring missing
rows would fabricate evidence.

### Decision 5: Make the decision gate explicit and conservative

The final decision label is computed from projection deltas, derived-field
failure share, executable pass deltas, safety/confirmation retention, renderer
coverage, deterministic roundtrip, and whether core slot failures remain
dominant.

Rationale: higher exact after removing fields is not model improvement. The
decision must distinguish schema burden reduction from semantic capability.

## Risks / Trade-offs

- Current prediction artifacts may not include row-level contracts in the
  expected location -> write `PROJECTION_BLOCKED_OR_INVALID` evidence and stop.
- Renderer templates may have low coverage -> classify as partial or blocked
  rather than improvising text.
- V2 Core can improve exact while executable quality does not improve -> report
  this as schema-burden evidence only, not model-quality improvement.
- Public reports may accidentally overstate Contract V2 readiness -> include
  explicit claims-not-to-overstate in decision, summary, README/CONTEXT, and
  Human Brief outputs.

## Migration Plan

This phase has no runtime migration. It adds experimental local-only code and
report artifacts. Rollback is removing the projection module, report command,
tests, report directory, and documentation truth-surface refresh.

## Open Questions

- If renderer coverage is below gate, should the next phase improve renderer
  policy or build a template-disjoint challenge set? This phase answers with a
  recommendation only; it does not implement the next step.
