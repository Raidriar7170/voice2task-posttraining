## ADDED Requirements

### Requirement: Validate shadow-mode input boundary
The system SHALL validate that shadow-mode integration uses only the current recovered raw inputs and the completed copy-backed verification slice evidence.

#### Scenario: Accepted shadow boundary
- **WHEN** the shadow-mode report is generated
- **THEN** it confirms the previous copy slice decision is `COPY_SLICE_READY_FOR_SHADOW_INTEGRATION`, enabled task-scoped triples are unchanged, `action` remains disabled, V1 evaluator metric delta is zero, raw input hashes are preserved, and no active OpenSpec predecessor is required
- **AND** it proceeds without reading superseded adapters, raw model logs, checkpoints, private rows, external services, or runtime browser state

#### Scenario: Invalid shadow boundary blocks output
- **WHEN** required source artifacts are missing, the previous copy slice is not ready, raw file hashes drift, action is enabled, or V1 evaluator zero-delta evidence is absent
- **THEN** the system writes `blocked.json` with `decision=SHADOW_MODE_BLOCKED_INVALID_INPUT`
- **AND** it MUST NOT write success summaries, shadow sidecars, enforcement recommendations, or model-quality claims

### Requirement: Attach copy-backed verifier as prediction-contract shadow sidecars
The system SHALL produce one deterministic sidecar row per Control/Treatment prediction contract without mutating the prediction contract.

#### Scenario: One sidecar per prediction contract
- **WHEN** shadow mode runs over the recovered dev/test Control/Treatment predictions
- **THEN** it writes exactly one shadow sidecar per `(split, sample_id, run_role)` prediction contract
- **AND** each sidecar includes `shadow_mode_enabled=true`, `enforcement_enabled=false`, `prediction_contract_hash`, `input_hash`, `policy_version`, and a deterministic nested `slot_diagnostics` list

#### Scenario: Prediction payload is immutable
- **WHEN** shadow sidecars are generated
- **THEN** recovered prediction files, gold files, evaluator inputs, `BrowserTaskContract` V1, `ContractCoreV2`, training targets, prompts, and runtime behavior remain unchanged
- **AND** the report proves raw input hashes and V1 evaluator metric deltas remain unchanged

### Requirement: Preserve task-scoped policy and action exclusion
The system SHALL reuse the previously approved task-scoped copy-backed policy without expanding enabled slots.

#### Scenario: Enabled slots remain query field target
- **WHEN** eligible prediction slots are verified in shadow mode
- **THEN** only task-scoped `query`, `field`, and `target` values from approved triples may receive `system_verified_source` provenance
- **AND** out-of-policy slots MUST be marked out-of-scope or unresolved in slot diagnostics

#### Scenario: Action stays disabled in shadow mode
- **WHEN** prediction contracts contain `action`
- **THEN** action diagnostics MUST have `verification_enabled=false`, `provenance=unresolved`, and no source-verified acceptance
- **AND** action counts MUST be reported separately as disabled analysis, not as a readiness gate success

### Requirement: Separate shadow provenance from correctness and enforcement
The system SHALL report shadow provenance, gold correctness side analysis, and enforcement status as distinct fields.

#### Scenario: Source verified does not imply correctness
- **WHEN** an eligible prediction value is source verified in a shadow sidecar
- **THEN** the report separately counts source-verified predictions, source-verified-and-gold-correct predictions, and source-verified-but-gold-mismatch predictions
- **AND** it MUST state that source-backed provenance is not task correctness, slot accuracy, executable quality, runtime readiness, or production readiness

#### Scenario: Shadow mode cannot enforce behavior
- **WHEN** a shadow sidecar contains failed, missing, ambiguous, unsupported, invalid, or out-of-scope diagnostics
- **THEN** the sidecar MUST NOT alter the prediction, suppress output, request clarification, or affect evaluator results
- **AND** `enforcement_enabled` MUST remain false for every sidecar

### Requirement: Report shadow-mode decision gates
The system SHALL publish deterministic shadow-mode metrics and exactly one final decision label.

#### Scenario: Required shadow metrics are present
- **WHEN** shadow-mode reporting completes
- **THEN** `summary.json` MUST include sidecar attachment count/rate, prediction contract count, enabled slot diagnostic count, out-of-scope diagnostic count, action disabled diagnostic count, source-verified prediction count/rate, source-verified-and-gold-correct count/rate, source-verified-but-gold-mismatch count/rate, fail-closed count/rate, provenance false accept count, silent fallback count, deterministic rerun rate, raw input hash preservation, V1 evaluator metric delta evidence, and enforcement enabled count

#### Scenario: Ready label requires all gates
- **WHEN** every shadow-mode gate is satisfied
- **THEN** the final decision label MAY be `SHADOW_MODE_READY_FOR_REVIEW`
- **AND** the only recommended next change MUST be `review-copy-backed-shadow-mode-before-runtime-wiring`

#### Scenario: Non-ready labels stay narrow
- **WHEN** input boundary is valid but shadow-mode readiness gates are not satisfied
- **THEN** the final decision label MUST be `SHADOW_MODE_PARTIAL_NEEDS_REFINEMENT` or `SHADOW_MODE_NOT_READY`
- **AND** the report MUST name exactly one bounded next change and MUST NOT recommend immediate runtime enforcement, action enablement, training, evaluator changes, or prediction repair

### Requirement: Publish compact public-safe shadow evidence
The system SHALL publish a compact public-safe evidence bundle and concise documentation for shadow-mode integration.

#### Scenario: Evidence bundle surface
- **WHEN** shadow-mode integration succeeds
- **THEN** `reports/public-sample/copy-backed-verification-shadow-mode/` MUST contain at most `summary.md`, `summary.json`, `shadow-sidecars.jsonl`, `shadow-compatibility.json`, `recommended-next-change.md`, and `blocked.json` only when blocked
- **AND** it MUST NOT include raw private rows, model outputs beyond current public-safe recovered contracts, checkpoints, adapters, raw logs, private paths, host details, SSH details, tokens, or secrets

#### Scenario: Documentation and Human Brief
- **WHEN** the phase completes
- **THEN** `docs/copy-backed-verification-shadow-mode.md` and a Chinese Human Brief MUST summarize shadow semantics, sidecar schema, verifier reuse, action exclusion, non-mutation proof, verification commands, evidence links, and claim boundaries
- **AND** they MUST NOT claim model improvement, slot accuracy improvement, executable quality improvement, runtime enforcement, production readiness, safety readiness, held-out recovery, or live-browser improvement
