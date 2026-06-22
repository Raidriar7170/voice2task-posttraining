## Context

The prior phase ended with `COPY_SLICE_READY_FOR_SHADOW_INTEGRATION` and named `integrate-copy-backed-slot-verification-shadow-mode` as the unique next change. That slice proved the verifier can attach system-owned source provenance for task-scoped `query`, `field`, and `target` values, but the output was a slot-level offline audit. This phase integrates the same verifier into a prediction-contract shadow sidecar surface.

The authoritative inputs are the recovered step-matched raw inputs, `reports/public-sample/copy-backed-slot-verification-slice/summary.json`, `task-scoped-policy.json`, `verification-audit.json`, the V1 schema/evaluator evidence, and current evidence-index/truth-surface files. This phase remains read-only over predictions and gold contracts.

## Goals / Non-Goals

**Goals:**

- Emit one deterministic shadow sidecar per Control/Treatment prediction contract.
- Reuse the existing copy-backed verifier and policy without changing matching semantics.
- Preserve a nested slot diagnostic list so verifier status can be compared per slot without mutating the prediction contract.
- Report shadow attachment coverage, enabled slot coverage, out-of-scope coverage, action-disabled counts, source-verified rates, gold-correct/mismatch side analysis, deterministic rerun evidence, raw input hash preservation, and V1 evaluator zero delta.
- Publish compact public-safe evidence and documentation that clearly separates shadow provenance from correctness and enforcement.

**Non-Goals:**

- No runtime enforcement, browser automation, action enablement, prediction repair, evaluator relaxation, schema migration, ContractCoreV2 change, prompt change, model training, prediction rerun, data mutation, LLM judge, fuzzy matching, semantic resolver, URL/date/entity resolver, production readiness claim, executable-quality claim, or model-improvement claim.

## Decisions

### Sidecar-per-prediction contract

Shadow mode writes one JSONL row per `(split, sample_id, run_role)` prediction contract. Each row contains a stable prediction contract hash, input hash, policy version, `shadow_mode_enabled=true`, and a nested `slot_diagnostics` list. This mirrors the unit that would be observed in a future shadow integration while remaining independent of the V1 contract payload.

Alternative considered: reuse the prior slot-level `verification-sidecars.jsonl` directly. That was rejected because it does not prove per-contract sidecar attachment or compatibility with prediction-level comparison surfaces.

### Reuse verifier and policy as read-only inputs

The shadow script imports `voice2task.copy_backed_slot_verification` and reads the archived slice policy. It does not copy matching logic into the script and does not widen normalization.

Alternative considered: regenerate a new policy from raw inputs. That would make this phase a policy-design change. This phase only integrates the previously approved policy and reports any boundary mismatch.

### Explicit shadow gates

The success label is `SHADOW_MODE_READY_FOR_REVIEW` only if the previous slice is ready, one sidecar exists for every Control/Treatment prediction contract, raw prediction/gold/input hashes are preserved, action remains disabled, provenance false accepts and silent fallbacks remain zero, deterministic rerun rate is 1.0, V1 evaluator delta is zero, and leak scan passes.

Alternative considered: mark ready based only on source-verified rate. That was rejected because source provenance is not correctness, and shadow-mode readiness must also prove sidecar attachment and non-mutation.

## Risks / Trade-offs

- [Risk] Shadow sidecars are mistaken for runtime enforcement. -> Mitigation: reports and docs state `shadow_mode_enabled=true` and `enforcement_enabled=false`, with no runtime file changes.
- [Risk] Source provenance is mistaken for task correctness. -> Mitigation: keep source-verified, source-verified-and-gold-correct, and source-verified-but-gold-mismatch as separate metrics.
- [Risk] Action scope leaks into enabled shadow mode. -> Mitigation: action diagnostics stay `OUT_OF_SCOPE` and action counts are reported as disabled.
- [Risk] Report generation mutates or reorders source artifacts. -> Mitigation: compute raw input hashes before/after and require V1 evaluator zero delta.
- [Risk] Sidecar file becomes a second contract schema. -> Mitigation: document it as diagnostic evidence only and avoid using it as evaluator input.

## Migration Plan

No runtime migration. After implementation, archive the OpenSpec change and stop. A later review phase may decide whether shadow-mode evidence is sufficient for a narrower runtime wiring proposal, but this phase must not implement enforcement or production behavior.
