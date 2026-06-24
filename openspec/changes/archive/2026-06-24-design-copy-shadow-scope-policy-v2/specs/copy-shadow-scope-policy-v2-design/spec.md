# copy-shadow-scope-policy-v2-design Specification

## ADDED Requirements

### Requirement: Validate Policy V2 design input boundary
The system SHALL validate the committed challenge v1, Policy V1, adapter evaluation, prediction, sidecar, evaluation-audit, and false-trust diagnosis artifacts before emitting Policy V2 design outputs.

#### Scenario: Accepted design input boundary
- **WHEN** the Policy V2 design engine starts
- **THEN** it verifies challenge hash, Policy V1 id/version/hash, adapter identity consistency, prediction/sidecar/audit alignment, collision downgrade evidence, technical false accept count, action/normalized attestation counts, execution eligibility count, V1 zero-delta evidence, and source-only sidecar semantics
- **AND** design outputs may be emitted only when all checks pass

#### Scenario: Invalid or inconsistent inputs block design
- **WHEN** any required input artifact is missing, drifted, misaligned, or contradictory
- **THEN** the system writes a bounded `blocked.json` report with a blocked decision label
- **AND** it MUST NOT emit an inactive Policy V2 proposal, mutate Policy V1, mutate challenge v1, mutate predictions, mutate sidecars, mutate audits, or change runtime behavior

### Requirement: Migrate false-trust mismatch taxonomy
The system SHALL split `CHALLENGE_FIXTURE_OR_GOLD_AMBIGUITY` into `TRUE_GOLD_OR_FIXTURE_AMBIGUITY` and `CANONICAL_STRING_MISMATCH` in the current diagnosis interpretation layer.

#### Scenario: Fixture-guided attribution is explicit
- **WHEN** a migrated mismatch row is written
- **THEN** the row records `attribution_mode=fixture_guided`, attribution source, condition tags used, deterministic checks used, and whether manual review is required
- **AND** attribution source MUST be one of `fixture_tag`, `deterministic_relation`, `fixture_tag_plus_deterministic_relation`, or `reviewed_fixture_ambiguity`

#### Scenario: Canonical string mismatch is low risk
- **WHEN** deterministic value-relation checks identify a canonical string mismatch
- **THEN** the primary mechanism is `CANONICAL_STRING_MISMATCH`
- **AND** the row is not counted as a high-risk mismatch for Policy V2 gates

#### Scenario: Fixture or gold ambiguity remains separate
- **WHEN** fixture tags or deterministic checks indicate true fixture or gold ambiguity
- **THEN** the primary mechanism is `TRUE_GOLD_OR_FIXTURE_AMBIGUITY`
- **AND** the row is reported separately from high-risk semantic mismatches

### Requirement: Compute post-hardening scope metrics
The system SHALL compute per-scope post-hardening metrics from committed diagnosis and evaluation artifacts without hard-coding final status by slot name.

#### Scenario: Scope metrics include gate evidence
- **WHEN** metrics are computed for a scope
- **THEN** the output records total attested count, per-adapter counts and rates, correct count/rate, Wilson 95 percent interval, high-risk mismatch count/rate, evidence sufficiency flags, current Policy V1 enabled state, technical false accept count, action/normalized attestation counts, and execution eligibility count

#### Scenario: High-risk mechanisms are bounded
- **WHEN** high-risk mismatch counts are computed
- **THEN** only `WRONG_ENTITY_FROM_SOURCE`, `SOURCE_ABSENT_SUBSTITUTION`, `OVERLONG_SOURCE_SPAN`, `UNDERSPECIFIED_PARTIAL_SPAN`, `WRONG_SLOT_OR_SCOPE_SELECTION`, `DUPLICATE_CONTEXT_DISAMBIGUATION_FAILURE`, and `GENERATED_VALUE_MISMATCH` count as high risk
- **AND** `NORMALIZATION_EQUIVALENCE_COLLISION`, `CANONICAL_STRING_MISMATCH`, and `TRUE_GOLD_OR_FIXTURE_AMBIGUITY` do not count as high risk

### Requirement: Compute deterministic scope gate status
The system SHALL compute one original gate status per scope using the configured gate order and thresholds.

#### Scenario: Observe enabled gate
- **WHEN** a scope has at least 30 attested samples, at least 10 Control and 10 Treatment samples, correct rate at least 0.90, Wilson lower bound at least 0.75, high-risk mismatch rate at most 0.05, adapter gap at most 0.10, zero technical false accepts, zero scope policy violations, and no unresolved semantic boundary
- **THEN** the original gate status is `OBSERVE_ENABLED`

#### Scenario: Observe limited gate
- **WHEN** a scope has at least 20 attested samples, at least 5 samples for each available adapter, correct rate at least 0.80, Wilson lower bound at least 0.60, high-risk mismatch rate at most 0.20, adapter gap at most 0.25, zero technical false accepts, and zero action/normalized attestation counts
- **THEN** the original gate status is `OBSERVE_LIMITED`

#### Scenario: Disable gate
- **WHEN** a scope has correct rate below 0.70, high-risk mismatch rate at least 0.25, technical false accepts above zero, policy violations above zero, mixed incompatible slot semantics, no engineering value, or high downstream misuse risk
- **THEN** the original gate status is `PROPOSE_DISABLE`

#### Scenario: Insufficient evidence gate
- **WHEN** a scope has fewer than 20 attested samples, only one adapter role, any available adapter count below 5, a Wilson interval that is too wide, overdependence on one condition, or insufficient fixture evidence for independent conclusion
- **THEN** the original gate status is `INSUFFICIENT_EVIDENCE`

#### Scenario: Candidate only fallback
- **WHEN** no earlier gate matches
- **THEN** the original gate status is `CANDIDATE_ONLY`

### Requirement: Apply downward-only review overrides
The system SHALL allow review overrides only when they move a scope to a more conservative status.

#### Scenario: Downward override is accepted
- **WHEN** a reviewer changes `OBSERVE_ENABLED` to `OBSERVE_LIMITED`, `OBSERVE_LIMITED` to `CANDIDATE_ONLY`, `CANDIDATE_ONLY` to `PROPOSE_DISABLE`, or `INSUFFICIENT_EVIDENCE` to `PROPOSE_DISABLE`
- **THEN** the decision records original gate status, final status, override direction, semantic reason, evidence reference, and reviewer requirement

#### Scenario: Upward override is rejected
- **WHEN** a reviewer attempts to move a scope to a less conservative status than its original gate status
- **THEN** the system rejects the override and fails validation

### Requirement: Emit inactive proposed Policy V2 artifact
The system SHALL write a proposed Policy V2 artifact only as an inactive review artifact.

#### Scenario: Proposed policy is inactive
- **WHEN** `configs/copy-backed-scope-policy-v2.proposed.json` is emitted
- **THEN** it records `status=proposal`, `active=false`, `runtime_loaded=false`, `enforcement_enabled=false`, source Policy V1 id/hash, decision gate version, challenge v1 hash, diagnosis artifact hash, and per-scope metrics, gate, final status, override, and evidence references
- **AND** no runtime loader or hook reads this proposed policy

### Requirement: Publish bounded design evidence
The system SHALL publish compact public-safe Policy V2 design evidence and documentation.

#### Scenario: Design evidence bundle is bounded
- **WHEN** the design run succeeds
- **THEN** `reports/public-sample/copy-shadow-scope-policy-v2-design/` contains at most `summary.md`, `summary.json`, `post-hardening-scope-metrics.json`, `gate-config.json`, `scope-decisions.json`, `taxonomy-migration.json`, `recommended-next-change.md`, and `blocked.json` only when blocked

#### Scenario: Documentation states review-only boundaries
- **WHEN** docs and the Human Brief are emitted
- **THEN** they state that Policy V2 is proposal-only, inactive, not runtime loaded, not enforcement, not action eligibility, not normalized trust, not training, not model improvement, and not a production or safety readiness claim

### Requirement: Select conservative design decision label
The system SHALL select exactly one final Policy V2 design decision label and one recommended next change.

#### Scenario: Scope reduction ready for review
- **WHEN** the deterministic gate engine succeeds, taxonomy migration succeeds, at least one scope is limited or disabled, proposed policy is complete and inactive, Policy V1 is unchanged, no upgrades occurred, technical false accepts are zero, and execution eligibility is false
- **THEN** the decision label is `POLICY_V2_SCOPE_REDUCTION_READY_FOR_REVIEW`
- **AND** the recommended next change is `review-and-freeze-copy-shadow-policy-v2-before-naturalistic-challenge`

#### Scenario: Design ready for review
- **WHEN** the deterministic gate engine succeeds but no scope-reduction-ready condition applies
- **THEN** the decision label is `POLICY_V2_DESIGN_READY_FOR_REVIEW`

#### Scenario: Design has insufficient evidence
- **WHEN** deterministic gate outputs show insufficient evidence prevents a review-ready scope decision
- **THEN** the decision label is `POLICY_V2_DESIGN_INSUFFICIENT_EVIDENCE`
- **AND** the recommended next change is `collect-independent-observe-only-evidence-for-copy-scopes`
