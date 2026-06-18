## Context

The current `CONTEXT.md` truth surface identifies the latest formal manifest as
`public-sample-20260617T152259Z`, with layered evaluation under
`reports/public-sample/layered-eval/`, residual diagnosis under
`reports/public-sample/residual-diagnosis/`, and residual-driven target
selection under `reports/public-sample/remediation-target-selection/`. That
target-selection phase ranked `slot-value-canonicalization-policy` as the second
recommended target after the safety repair design path. The dominant residual
families include `slot_value_mismatch=336`,
`normalized_command_mismatch=194`, `extra_slot=16`, `missing_slot=13`, and
`route_mismatch=13` / `task_type_mismatch=13`.

This phase is a policy/design phase. It must use committed public-safe evidence
and schema/test surfaces to define canonical target-writing boundaries without
modifying formal data, predictions, strict evaluator behavior, or model
artifacts.

## Goals / Non-Goals

**Goals:**

- Publish the requested policy files under
  `reports/public-sample/slot-canonicalization-policy/`.
- Define a deterministic slot key policy with canonical keys, aliases,
  disallowed keys, task-type-specific required/optional keys, and examples.
- Define conservative slot value normalization boundaries and explicit
  non-equivalence cases for later data rematerialization and layered diagnostics.
- Reposition `normalized_command` as diagnostic/display-oriented and document
  when deterministic template generation should replace free model generation.
- Define the model-target versus deterministic-postprocessor boundary for
  route, task type, slots, safety, confirmation, derived fields, and runtime
  hints.
- Map residual families to recommended remediation strategies and select a
  bounded next change without implementing it.
- Add tests that keep the policy deterministic, public-safe, and strict-exact
  preserving.

**Non-Goals:**

- No training, prediction rerun, A100 job, public-sample data merge, new
  SFT/DPO rows, split change, LoRA/base-model change, prompt change, evaluator
  definition change, strict-exact relaxation, slot normalization in strict
  exact, LLM judge, semantic-equivalence scoring, prediction repair,
  checkpoint/adapter release, model-improvement claim, held-out recovery claim,
  production-readiness claim, safety-readiness claim, or live-browser benchmark
  claim.

## Decisions

1. **Write policy artifacts directly from committed public evidence.**
   The implementation should not rerun predictions or inspect private corpora.
   The reports should cite `CONTEXT.md`, `layered-eval`, `residual-diagnosis`,
   `remediation-target-selection`, public schema/test examples, and existing
   dataset/evaluation docs as their evidence base.

2. **Keep strict exact match untouched.**
   Conservative slot-value normalization may be documented for later label
   policy, deterministic layered diagnostics, or data review, but it must not
   rewrite gold/prediction values, repair predictions, or affect strict exact.

3. **Treat slot keys as schema policy, not semantic guessing.**
   Alias rules should cover stable vocabulary such as `keyword/search_text` to
   `query`, `webpage/site` to `url`, and `field/form_field` to `field_name`,
   while explicitly refusing unsafe merges such as arbitrary
   `product_name`/`query` or `location`/`destination` outside task-specific
   context.

4. **Move derived contract fields out of free-form model targets.**
   If `allowed_actions`, `success_criteria`, display normalized commands,
   policy tags, confirmation defaults, or runtime hints can be derived from
   `route`, `task_type`, `slots`, `risk_level`, and confirmation/refusal
   decisions, they should be postprocessor-derived or validated in later
   phases. This narrows the model output target and reduces avoidable strict
   exact failures.

5. **Make the next change a recommendation, not an implementation.**
   `recommended-next-change.md` should choose between a canonical slot-boundary
   candidate materialization phase and a deterministic postprocessor phase based
   on current residual evidence. This phase must not materialize data or build
   the postprocessor.

## Risks / Trade-offs

- [Risk] Policy language could be mistaken for a new evaluator definition. ->
  Mitigation: every artifact states that strict exact remains unchanged and
  normalization is not used to re-score prior evidence.
- [Risk] Alias mapping could overmerge semantically different fields. ->
  Mitigation: include non-equivalence cases and task-type-scoped key rules.
- [Risk] Derived-field guidance could be treated as implemented behavior. ->
  Mitigation: keep implementation flags and recommended next change explicit;
  this phase writes policy only.
- [Risk] Existing active OpenSpec work could be conflated with this new phase.
  -> Mitigation: this phase writes only `slot-canonicalization-policy` artifacts
  and leaves other active changes and historical evidence untouched.
