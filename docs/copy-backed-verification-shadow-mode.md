# Copy-backed Verification Shadow Mode

This document describes the bounded shadow-mode integration for the copy-backed verifier.

## Shadow semantics

Shadow mode emits one sidecar row for each current Control/Treatment prediction contract. The sidecar records `shadow_mode_enabled=true` and `enforcement_enabled=false`, then nests slot-level verifier diagnostics under `slot_diagnostics`.

## Sidecar schema

Each sidecar contains `sample_id`, `split`, `run_role`, `task_type`, `route`, `prediction_contract_hash`, `input_hash`, `source_text_hash`, `policy_version`, and deterministic slot diagnostics. The sidecar is not a replacement contract and is not an evaluator input.

## Verifier reuse

The script reuses `voice2task.copy_backed_slot_verification` and the previous task-scoped policy. It does not widen normalization, add semantic matching, call an LLM, resolve URLs, or repair predictions.

## Action remains disabled

Action remains disabled in shadow mode. Action diagnostics are out-of-scope analysis only and receive no source-verified provenance.

## Evidence

- Decision: `SHADOW_MODE_READY_FOR_REVIEW`.
- Sidecar attachment rate: 1.000000.
- Source-verified prediction rate: 0.874419.
- V1 evaluator zero delta: True.
- Enforcement enabled count: 0.
- Action source-verified count: 0.

## Claim boundary

No training, prediction rerun, data mutation, V1 schema migration, ContractCoreV2 change, evaluator relaxation, action enablement, runtime enforcement, model improvement claim, slot accuracy claim, executable quality claim, production readiness claim, held-out recovery claim, or live browser claim occurred.
