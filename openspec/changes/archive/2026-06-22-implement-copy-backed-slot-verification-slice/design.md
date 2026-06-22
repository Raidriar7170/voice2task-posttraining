## Context

The prior design phase ended with `HYBRID_DESIGN_READY_COPY_SLICE_FIRST` and recommended `implement-copy-backed-slot-verification-slice`. The current implementation boundary is narrower than the design's global copy candidates: enabled verification covers only task-scoped `query`, `field`, and `target`; `action` is analyzed but disabled because its semantics are tied to blocked/clarify/safety contexts.

The current authoritative inputs are recovered step-matched raw inputs, hybrid representation design artifacts, slot error analysis artifacts, internal ContractCoreV2 evidence, the formal public sample manifest, and existing V1 schema/evaluator code. This implementation produces sidecar diagnostics only.

## Goals / Non-Goals

**Goals:**

- Verify eligible string slot values against `input_text` with exact unique and bounded normalized unique source spans.
- Preserve Unicode character offsets, `start` inclusive and `end` exclusive, with exact back-slice validation.
- Fail closed for ambiguous, not-found, unsupported, invalid, and out-of-scope cases.
- Keep task-scoped eligibility explicit by `(task_type, route, slot_path)`.
- Report gold feasibility separately from prediction provenance and prediction correctness side analysis.
- Prove provenance false accepts and silent fallbacks are zero.

**Non-Goals:**

- No training, A100/GPU work, prediction rerun, data mutation, schema migration, evaluator relaxation, model prompt change, runtime integration, shadow enforcement, URL resolver, ambiguity/reason implementation, action enablement, model improvement claim, slot accuracy claim, or executable-quality claim.

## Decisions

### Standalone verifier module

Add `src/voice2task/copy_backed_slot_verification.py` with dataclasses for `CopyBackedScope`, `SourceSpan`, and `CopyBackedVerificationResult`. This avoids expanding `slot_error_analysis.py`, `contract_core_v2.py`, or evaluator modules.

### Conservative normalized matching

The verifier supports exact substring lookup first. Normalized lookup uses a character-preserving mapping over Unicode NFKC, casefold, and omission of whitespace/punctuation separators. It does not use semantic aliases, date conversion, city/product aliases, URL resolver, LLM normalization, embeddings, or distance heuristics.

### Sidecar-only reporting

Prediction contracts and gold contracts remain immutable inputs. Verified provenance is written only to `verification-sidecars.jsonl` and aggregate reports; it is never written back into V1 contracts and is not an evaluator input.

### Decision label gate

The success label is `COPY_SLICE_READY_FOR_SHADOW_INTEGRATION` only if enabled scopes are task-scoped, gold unique verified rate is at least 0.70, provenance false accepts are zero, silent fallbacks are zero, deterministic rerun rate is 1.0, V1 evaluator metrics have zero delta, source span roundtrip pass rate is 1.0, and leak scan is clean. Otherwise the report must select a narrower partial/not-justified/blocked label.

## Risks / Trade-offs

- [Risk] Source verification is mistaken for task correctness. -> Mitigation: report source-verified-and-gold-mismatch separately and state source provenance is not prediction correctness.
- [Risk] Duplicate spans are silently accepted. -> Mitigation: duplicates return `AMBIGUOUS_MULTIPLE_MATCHES` and fail closed.
- [Risk] Normalization drifts into semantic matching. -> Mitigation: allowlist only character-level normalization with offset mapping and tests for non-matching cities, dates, and products.
- [Risk] Action scope leaks into enabled verification. -> Mitigation: action policy rows are `enabled=false`, sidecars remain out-of-scope, and action metrics are reported separately.
- [Risk] Report generation changes historical metrics. -> Mitigation: compare committed raw-input metric reproduction before and after report generation and require zero deltas.

## Migration Plan

This phase has no runtime migration. After implementation, archive the OpenSpec change and stop. A future change may consider `integrate-copy-backed-slot-verification-shadow-mode`, but this phase must not implement it.
