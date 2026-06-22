# copy-backed-slot-verification Specification

## Purpose
Define the offline copy-backed slot verification slice for Voice2Task: task-scoped eligibility, verifier-owned source spans/provenance, bounded normalization, fail-closed sidecars, provenance/correctness separation, and compact public-safe evidence while BrowserTaskContract V1 remains the external schema.
## Requirements
### Requirement: Validate copy-slice input boundary
The system SHALL validate that the copy-backed verification slice uses only the current public-safe recovered raw inputs, Hybrid Slot Representation V1 artifacts, slot error analysis evidence, internal ContractCoreV2 evidence, V1 schema/evaluator evidence, and the formal public sample manifest.

#### Scenario: Accepted slice boundary
- **WHEN** the copy-backed verification report is generated
- **THEN** it confirms the hybrid design decision is `HYBRID_DESIGN_READY_COPY_SLICE_FIRST`, recovered raw inputs are metric-reproduced, external serialization remains `BrowserTaskContract` V1, training targets are unchanged, and predictions/gold contracts are read-only inputs
- **AND** it proceeds without reading superseded adapter outputs, raw model logs, checkpoints, private rows, or external services

#### Scenario: Invalid slice boundary blocks output
- **WHEN** any required source artifact is missing, inconsistent, or outside the allowed boundary
- **THEN** the system writes a blocked artifact with `decision=COPY_SLICE_BLOCKED_INVALID_INPUT`
- **AND** it MUST NOT write success summaries, sidecars, shadow-integration recommendations, or model-quality claims

### Requirement: Build task-scoped eligibility policy
The system SHALL derive a deterministic eligibility policy keyed by `(task_type, route, slot_path)` before verifying predictions.

#### Scenario: Eligible copy-backed triples are explicit
- **WHEN** the policy is generated
- **THEN** enabled triples MUST be restricted to task-scoped `query`, `field`, and `target` slot paths with sufficient sample count, copyability at or above the configured threshold, HIGH or MEDIUM prior confidence, and fail-closed behavior
- **AND** the policy MUST report `strategy_assignment_rate` and `copy_strategy_candidate_coverage` as renamed historical design metrics, not as verified span rates

#### Scenario: Action stays disabled
- **WHEN** `action` slot paths are encountered
- **THEN** they MUST be analyzed as disabled policy rows with an exclusion reason
- **AND** no `action` value may receive verified provenance or be counted as an acceptance gate in this phase

### Requirement: Verify exact and bounded-normalized source spans
The system SHALL verify eligible string values against the original `input_text` with deterministic source-span lookup.

#### Scenario: Exact unique span succeeds
- **WHEN** an eligible string value appears exactly once in `input_text`
- **THEN** the verifier returns `VERIFIED_EXACT_UNIQUE`, `match_kind=exact`, `provenance=system_verified_source`, a source text hash, and half-open Unicode character offsets whose back-slice equals the original source substring

#### Scenario: Bounded normalized unique span succeeds
- **WHEN** exact lookup fails and the allowlisted normalized value appears exactly once in normalized source text
- **THEN** the verifier returns `VERIFIED_NORMALIZED_UNIQUE`, `match_kind=normalized`, `provenance=system_verified_source`, and original-source offsets mapped from the normalized match
- **AND** the normalization MUST be limited to Unicode NFKC, casefolding, and whitespace/punctuation separator omission with no semantic aliasing, date conversion, city/product mapping, URL resolver, LLM, embedding, or fuzzy matching

#### Scenario: Non-unique or absent spans fail closed
- **WHEN** lookup finds multiple spans, no span, unsupported value type, invalid input, or an out-of-scope slot
- **THEN** the verifier returns one of `AMBIGUOUS_MULTIPLE_MATCHES`, `NOT_FOUND`, `UNSUPPORTED_VALUE_TYPE`, `INVALID_INPUT`, or `OUT_OF_SCOPE`
- **AND** provenance MUST be `unresolved` and the value MUST NOT be silently repaired or counted as verified

### Requirement: Publish sidecar-only provenance evidence
The system SHALL write verifier outputs as sidecar evidence without changing contracts, data, evaluator inputs, model outputs, training targets, schemas, or runtime behavior.

#### Scenario: Prediction contracts are immutable
- **WHEN** Control and Treatment predictions are verified
- **THEN** provenance appears only in `verification-sidecars.jsonl` and aggregate reports
- **AND** recovered prediction files, gold files, V1 evaluator outputs, `BrowserTaskContract` V1, and `ContractCoreV2` remain behaviorally unchanged

#### Scenario: Provenance and correctness stay separate
- **WHEN** a prediction value is source verified
- **THEN** the report separately counts source-verified predictions, source-verified-and-gold-correct predictions, and source-verified-but-gold-mismatch predictions
- **AND** it MUST state that source-backed provenance is not task correctness, slot accuracy, executable quality, or production readiness

### Requirement: Report fail-closed metrics and decision label
The system SHALL report all required counts/rates and select exactly one final decision label for this bounded slice.

#### Scenario: Required metrics are present
- **WHEN** the verification audit completes
- **THEN** `summary.json` MUST include `eligible_copy_event_count`, unique exact and normalized span rates, duplicate ambiguity rate, span-not-found rate, unsupported value type count, out-of-scope count, source-verified prediction rate, source-verified-and-gold-correct rate, source-verified-gold-mismatch rate, fail-closed rate, `provenance_false_accept_count`, `silent_fallback_count`, deterministic rerun rate, source span roundtrip pass rate, and V1 evaluator metric delta evidence

#### Scenario: Ready label requires all gates
- **WHEN** every acceptance gate is satisfied
- **THEN** the final decision label MAY be `COPY_SLICE_READY_FOR_SHADOW_INTEGRATION` and the only recommended next change is `integrate-copy-backed-slot-verification-shadow-mode`

#### Scenario: Non-ready labels stay narrow
- **WHEN** readiness gates are not satisfied but the input boundary is valid
- **THEN** the final decision label MUST be `COPY_SLICE_PARTIAL_NEEDS_SCOPE_REFINEMENT` or `COPY_SLICE_NOT_JUSTIFIED`
- **AND** the report MUST name exactly one bounded next change and MUST NOT expand into training, evaluator changes, prediction repair, action enablement, or runtime integration

### Requirement: Publish compact public-safe evidence surface
The system SHALL publish a compact public-safe evidence bundle and concise documentation for the copy-backed verification slice.

#### Scenario: Evidence bundle surface
- **WHEN** the slice succeeds
- **THEN** `reports/public-sample/copy-backed-slot-verification-slice/` MUST contain at most `summary.md`, `summary.json`, `task-scoped-policy.json`, `verification-audit.json`, `recommended-next-change.md`, and optionally `verification-sidecars.jsonl`
- **AND** `blocked.json` MUST be absent unless the slice is blocked

#### Scenario: Documentation and Human Brief
- **WHEN** the slice completes
- **THEN** `docs/copy-backed-slot-verification.md` and a Chinese Human Brief MUST summarize source-span semantics, fail-closed behavior, action exclusion, provenance/correctness separation, verification commands, evidence links, and claim boundaries
- **AND** they MUST NOT claim model improvement, stricter evaluator success, executable quality improvement, live-browser readiness, production readiness, or held-out recovery
