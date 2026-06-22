## Context

The previous slot error mechanism analysis is the active evidence source for this change. It reports `MIXED_SLOT_REPRESENTATION_REQUIRED` across 414 dev/test samples and 471 gold slot events: exact/normalized source-copyable gold slots are about 50.53%, source-absent or generation-required slots are about 49.47%, typed-derivable coverage is 0.00%, and current prediction values unsupported by source are about 32.17%. Control to Treatment slot movement is recovered=10, regressed=12, net=-2, so the evidence does not justify another training claim or metric-improvement claim.

Current external behavior remains `BrowserTaskContract` V1. `ContractCoreV2` remains an internal core/envelope boundary and is not being changed by this phase. The current training target remains V1 contract JSON. This change only designs a future internal slot boundary and quantifies representation feasibility from current public-safe artifacts.

## Goals / Non-Goals

**Goals:**

- Define the recommended internal Hybrid Slot Representation V1 fields and ownership boundaries.
- Select representation strategies per task type and slot path from current evidence, not from slot names alone.
- Define source-span offset semantics, verifier-owned provenance, allowlisted normalization semantics, and unsupported fail-closed behavior.
- Compare future model-target options for value/snippet/offset output and choose a primary recommendation.
- Produce a read-only offline feasibility projection and one next vertical-slice recommendation.

**Non-Goals:**

- No training, DPO, GRPO, A100/GPU job, data expansion, prediction rerun, prediction repair, LLM judge, semantic-equivalence scoring, evaluator relaxation, checkpoint/adapter release, or live-browser claim.
- No change to `BrowserTaskContract` V1, `ContractCoreV2`, evaluator logic, layered evaluator, current training target, gold contracts, recovered predictions, downstream runtime, or public schema.
- No implementation of a production span resolver, typed normalizer, task-specific slot validator, runtime DTO, training formatter, or downstream integration.

## Decisions

### HybridSlotValue shape is internal and verifier-owned

Recommended fields:

- `value`: model-authored slot value or bounded structured value.
- `value_type`: system-derived coarse type such as `text`, `number`, `boolean`, `object`, `list`, or `null`.
- `representation_kind`: system-derived strategy: `copy`, `copy_then_normalize`, `enum`, `task_schema_constrained`, `bounded_structured`, `limited_free_generation`, or `unresolved`.
- `source_span`: optional verifier-owned half-open source offsets.
- `normalization_rule`: optional verifier-owned allowlisted rule.
- `verification_status`: system-derived `verified`, `unsupported`, or `unresolved`.
- `provenance`: system-derived `source_verified`, `deterministic_derived`, `schema_constrained`, `structured_generated`, `free_generated`, or `unknown`.
- `fallback_behavior`: system-derived `emit_v1_value`, `fail_closed`, `clarify`, `diagnostic_only`, or `resolver_required`.

Rationale: the model can author values or bounded structures, but it must not be trusted to declare verified provenance, source hashes, verification status, or normalization rules. This prevents feasibility evidence from being mistaken for implemented quality.

Alternative considered: model directly emits a full `HybridSlotValue`. This is rejected for V1 because it gives the model authority over provenance and verifier state, making unsupported cases harder to fail closed.

### Source spans use source text half-open Unicode offsets

The source span is based on the original input text or a fixed sanitized transcript. Offsets use Unicode character positions, `start` inclusive and `end` exclusive, with `source_text_hash` recorded by the system. A verified copy requires `source_text[start:end]` to exactly recover the source substring before any allowlisted normalization is applied. Spans are contiguous; multi-span values require an explicit list representation. String similarity alone cannot create a verified span.

Alternative considered: byte offsets. This is rejected for this design because Chinese ASR transcripts and JSON text processing are easier to verify consistently with Unicode character offsets in Python and documentation artifacts.

### Future model target defaults to value output plus system verification

Primary recommendation: the model outputs the V1-compatible value, and the system verifies and attaches source span/provenance after prediction.

Fallback: the model may output a candidate source snippet for specifically approved copy-heavy slots, but the snippet remains an untrusted pointer and the system must still resolve and verify offsets.

Rejected for V1: direct model output of `start`/`end` offsets. It is more brittle for Chinese and ASR transcript edits, increases JSON complexity, and is less compatible with current V1 targets and 7B generative behavior.

### Representation strategy is evidence-driven

High copyability paths such as `query`, `field`, `target`, and `action` are candidates for `copy` or `copy_then_normalize`, subject to task scope and verification. `ambiguity` and many `reason` cases are candidates for `bounded_structured` or, when evidence is insufficient, `limited_free_generation` with a narrow whitelist. `url` requires a three-way design: exact/normalized copy, deterministic resolver/allowlist, or unresolved/clarify. Key-boundary issues are handled by `task_schema_constrained`, but this does not replace value extraction.

Alternative considered: convert all slots to spans. This is rejected because about half of gold slots are source-absent or generation-required. Alternative considered: keep all slots as unrestricted free generation. This is rejected because copyable fields and unsupported predictions need deterministic verification and fail-closed behavior.

## Risks / Trade-offs

- [Risk] Representation feasibility is retold as model improvement. -> Mitigation: reports and docs must label it as design-only and avoid slot accuracy, executable pass, held-out recovery, or production-readiness claims.
- [Risk] Internal representation drifts from V1 serialization. -> Mitigation: compatibility section must state V1 remains the external contract and future implementation needs roundtrip tests.
- [Risk] Normalization becomes evaluator relaxation. -> Mitigation: normalization rules are verifier-owned allowlist metadata and do not alter current strict metrics in this phase.
- [Risk] Ambiguity/reason taxonomy is invented beyond evidence. -> Mitigation: bounded structures are proposed only from observed current slot paths and are marked partial when evidence is thin.
- [Risk] URL resolver semantics are underspecified. -> Mitigation: resolver behavior remains a design boundary, not an implementation, unless future evidence identifies an allowlist source.

## Migration Plan

This phase has no runtime migration. It creates OpenSpec artifacts, a design document, read-only feasibility reports, tests, and concise truth-surface updates. A future implementation phase must choose one vertical slice, preserve V1 external serialization, and add verifier tests before any runtime use.

## Open Questions

- Which URL resolver allowlist, if any, is authoritative enough for future deterministic URL derivation?
- Which ambiguity/reason subtypes have enough data to become stable bounded structures instead of limited generated text?
- Should a future copy-heavy slice use value-only model output exclusively, or allow an untrusted snippet fallback for duplicate-text disambiguation?
