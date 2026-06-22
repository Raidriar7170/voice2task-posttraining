# Hybrid Slot Representation V1

## Problem statement

The current slot-analysis decision is `MIXED_SLOT_REPRESENTATION_REQUIRED`: copyable paths and generation-required paths coexist, so a single span-only or unrestricted-generation representation would be inaccurate.

## Evidence summary

- Samples: 414 dev/test samples.
- Gold slot events: 471.
- Gold exact/normalized source-copyable rate: 50.53%.
- Source-absent or generation-required rate: 49.47%.
- Typed-derivable coverage: 0.00%.
- Prediction unsupported-by-source rate: 32.17%.
- Control to Treatment movement: recovered=10, regressed=12, net=-2.

## Design principles

- Keep external `BrowserTaskContract` V1 unchanged.
- Keep current `ContractCoreV2` unchanged.
- Treat this as a future internal slot boundary proposal, not a schema implementation.
- Make source span, provenance, normalization, and verification status system-derived.
- Fail closed for unsupported or unverifiable values.
- Do not convert all slots to spans or keep all slots as unrestricted free generation.

## Internal proposal

`HybridSlotValue` final proposed fields:

- `value` (model): V1-compatible slot value or bounded structured value authored by the model.
- `value_type` (system): Coarse type derived from the value: text, number, boolean, object, list, null, or unknown.
- `representation_kind` (system): Primary representation strategy selected from evidence and task scope.
- `source_span` (system): Optional verifier-owned source slice containing start, end, text, and source_text_hash.
- `normalization_rule` (system): Optional allowlisted deterministic normalization rule applied after source back-slice validation.
- `verification_status` (system): Verifier result: verified, unsupported, or unresolved.
- `provenance` (system): Verifier provenance: source_verified, deterministic_derived, schema_constrained, structured_generated, free_generated, or unknown.
- `fallback_behavior` (system): Fail-closed outcome: emit_v1_value, fail_closed, clarify, diagnostic_only, or resolver_required.

`source_span` contains `start`, `end`, `text`, and `source_text_hash`. The hash is system-derived from the source text.

## Source-span semantics

Source span offsets are Unicode character offsets over the original input text or fixed sanitized transcript. `start` is inclusive, `end` is exclusive, and `source_text[start:end]` must exactly recover the verified source text before normalization. Similarity-only spans are not verified copy. Discontiguous spans require an explicit list representation.

## Representation kinds

- `copy`: value should be source-backed and verifier-owned span/provenance must succeed.
- `copy_then_normalize`: value comes from source and then uses an allowlisted deterministic normalization rule.
- `enum`: finite schema/policy value only.
- `task_schema_constrained`: key boundary validation for required/optional/forbidden slot keys.
- `bounded_structured`: finite structure for generation-required fields such as ambiguity/reason.
- `limited_free_generation`: narrow whitelist only when copy, normalization, enum, and structure do not apply.
- `unresolved`: verifier cannot prove the value; future policy may clarify, reject, or fallback.

## Model-authored vs system-derived fields

Model-authored:

- `value` or a bounded structure.
- enum/code only when that strategy requires it.

System-derived:

- `value_type`, `representation_kind`, verified `source_span`, `normalization_rule`, `verification_status`, `provenance`, `source_text_hash`, task-key validation result, fallback decision, and runtime compatibility metadata.

模型不需要直接输出 offsets；主推荐是模型输出 value，系统验证并附加 source span。Snippet may be retained as one fallback candidate pointer for approved copy-heavy slots, but it remains untrusted until verified.

Future model-target option comparison:

- Option A `model_outputs_value_system_verifies_span`: primary; fit=best fit because current model already emits V1 slot values; V1=best; no target migration required
- Option B `model_outputs_candidate_source_snippet_system_resolves_offset`: fallback_for_approved_copy_heavy_slots; fit=usable only as a narrowed fallback; V1=requires additional internal candidate pointer metadata
- Option C `model_outputs_start_end_offsets`: rejected_for_v1; fit=poor without a new target and focused training; V1=weak; requires target migration

## Task-specific slot policy

- `blocked:deny`: required=['reason']; optional=['action']; forbidden=['unknown_unlisted_keys']; alias=canonicalization_candidate_only; strict historical evaluator unchanged; unknown=fail_closed_or_diagnostic_only; missing=unresolved_or_clarify; extra=validation_failure_or_diagnostic_only
- `clarify:clarify`: required=['ambiguity']; optional=[]; forbidden=['unknown_unlisted_keys']; alias=canonicalization_candidate_only; strict historical evaluator unchanged; unknown=fail_closed_or_diagnostic_only; missing=unresolved_or_clarify; extra=validation_failure_or_diagnostic_only
- `extract:extract_page`: required=['target']; optional=[]; forbidden=['unknown_unlisted_keys']; alias=canonicalization_candidate_only; strict historical evaluator unchanged; unknown=fail_closed_or_diagnostic_only; missing=unresolved_or_clarify; extra=validation_failure_or_diagnostic_only
- `form_fill:fill_form`: required=['field']; optional=[]; forbidden=['unknown_unlisted_keys']; alias=canonicalization_candidate_only; strict historical evaluator unchanged; unknown=fail_closed_or_diagnostic_only; missing=unresolved_or_clarify; extra=validation_failure_or_diagnostic_only
- `navigate:open_url`: required=['url']; optional=[]; forbidden=['unknown_unlisted_keys']; alias=canonicalization_candidate_only; strict historical evaluator unchanged; unknown=fail_closed_or_diagnostic_only; missing=unresolved_or_clarify; extra=validation_failure_or_diagnostic_only
- `search:search_web`: required=['query']; optional=[]; forbidden=['unknown_unlisted_keys']; alias=canonicalization_candidate_only; strict historical evaluator unchanged; unknown=fail_closed_or_diagnostic_only; missing=unresolved_or_clarify; extra=validation_failure_or_diagnostic_only

Alias handling is diagnostic/canonicalization-candidate only and does not change the historical strict evaluator.

## Clarify ambiguity design

Recommended shape: `ambiguity_type` enum plus `related_slot_keys` and optional `display_text`. Candidate observed categories are `missing_information`, `unresolved_reference`, `multiple_targets`, and `insufficient_context`. This reduces unrestricted generation while still mapping back to current V1 `slots.ambiguity` in a future implementation.

## Reason design

Recommended shape: bounded reason code or deterministic reference to `safety.reason` when the reason is policy-derived. Avoid duplicating the same safety rationale across `safety.reason`, `slots.reason`, and `normalized_command`. This is a de-duplication proposal only.

## URL design

URL uses a three-way strategy: exact/normalized copy when source-supported, deterministic resolver only if a future allowlist source is defined, otherwise unresolved/clarify. This phase does not implement a resolver and does not classify every source-absent URL as hallucination.

## V1 / ContractCoreV2 compatibility

External schema remains `BrowserTaskContract` V1. Current training targets remain V1 contract JSON. Current `ContractCoreV2` remains an internal core/envelope boundary. The hybrid representation is not serialized to public runtime contracts in this phase.

## Offline feasibility results

- Overall representation coverage: 100.00%
- Copy-backed coverage: 57.32%
- Copy-normalize possible coverage: 1.70%
- Bounded structured coverage: 31.21%
- Limited free-generation coverage: 0.00%
- Unresolved coverage: 11.46%
- Currently verifiable prediction rate: 51.80%
- Currently fail-closed prediction rate: 48.20%

Representation matrix:

| Slot path | Scope | Proposed representation | Confidence | Fallback | Evidence |
| --- | --- | --- | --- | --- | --- |
| action | blocked:deny, clarify:clarify | `copy` | HIGH | fail_closed_or_unresolved_when_span_not_verified | reports/public-sample/slot-error-mechanism-analysis/slot-profile.json#action |
| ambiguity | clarify:clarify, form_fill:fill_form | `bounded_structured` | HIGH | clarify_or_unresolved_when_structure_not_supported | reports/public-sample/slot-error-mechanism-analysis/slot-profile.json#ambiguity |
| city | clarify:clarify | `task_schema_constrained` | LOW | diagnostic_only_until_validator_slice | reports/public-sample/slot-error-mechanism-analysis/slot-profile.json#city |
| field | clarify:clarify, form_fill:fill_form | `copy` | HIGH | fail_closed_or_unresolved_when_span_not_verified | reports/public-sample/slot-error-mechanism-analysis/slot-profile.json#field |
| query | clarify:clarify, extract:extract_page, search:search_web | `copy` | HIGH | fail_closed_or_unresolved_when_span_not_verified | reports/public-sample/slot-error-mechanism-analysis/slot-profile.json#query |
| reason | blocked:deny, clarify:clarify, form_fill:fill_form | `bounded_structured` | HIGH | clarify_or_unresolved_when_structure_not_supported | reports/public-sample/slot-error-mechanism-analysis/slot-profile.json#reason |
| target | extract:extract_page | `copy` | MEDIUM | fail_closed_or_unresolved_when_span_not_verified | reports/public-sample/slot-error-mechanism-analysis/slot-profile.json#target |
| url | clarify:clarify, navigate:open_url | `unresolved` | MEDIUM | resolver_required_or_clarify | reports/public-sample/slot-error-mechanism-analysis/slot-profile.json#url |

## Recommended vertical slice

Primary next change: `implement-copy-backed-slot-verification-slice`.

Why: query/field/target/action have high observed copyability, the slice can run offline without training, and verifier-owned span/provenance can fail closed while preserving V1.

Fallback: `implement-task-specific-slot-schema-validator` if copy verification ambiguity blocks implementation.

## Migration risks

- Internal representation could drift from V1 serialization.
- Typed normalization could be mistaken for evaluator relaxation.
- Span provenance could be overclaimed without deterministic verifier evidence.
- URL resolver semantics are not yet authoritative.
- Ambiguity/reason structures can become free generation unless bounded.

## Claim boundaries

This is representation feasibility, not model improvement. It does not mutate predictions, repair outputs, rerun evaluation, or recalculate model success metrics.

## Current claims that remain unsupported

- slot accuracy improved
- executable pass improved
- span extraction works in production
- hybrid representation is implemented
- new training target is active
- V1 schema has migrated
- production or safety readiness
- held-out recovery
- live browser improvement

## Non-goals

No training, prediction rerun, data mutation, schema implementation, runtime integration, evaluator modification, model target change, LLM judge, prediction repair, span extraction model, typed normalizer, task-specific validator implementation, checkpoint/adapter release, production readiness, or live-browser improvement.
