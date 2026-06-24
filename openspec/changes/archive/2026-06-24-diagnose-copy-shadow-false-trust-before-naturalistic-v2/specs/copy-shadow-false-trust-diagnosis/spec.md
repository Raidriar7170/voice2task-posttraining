## ADDED Requirements

### Requirement: Validate diagnosis input boundary
The system SHALL validate the frozen challenge, policy, adapter-evaluation artifacts, prediction outputs, sidecars, audits, and invariance evidence before running false-trust diagnosis.

#### Scenario: Accepted committed input boundary
- **WHEN** false-trust diagnosis starts
- **THEN** the system verifies challenge hash, policy id/version/hash, adapter identity status, prediction artifact alignment with challenge ids, sidecar alignment with predictions, evaluation audit alignment with gold, prediction output invariance, V1 evaluator zero-delta, `action_trusted_count=0`, and `normalized_trusted_count=0`
- **AND** diagnosis may proceed only after all checks pass

#### Scenario: Invalid input boundary blocks diagnosis
- **WHEN** any required source artifact is missing, inconsistent, drifted, or misaligned
- **THEN** the system writes `blocked.json` with `decision=FALSE_TRUST_DIAGNOSIS_BLOCKED_INVALID_INPUT` or `decision=FALSE_TRUST_DIAGNOSIS_INCONSISTENT_ARTIFACTS`
- **AND** it MUST NOT modify challenge rows, gold, policy v1, predictions, online sidecars, offline audits, evaluator logic, model artifacts, prompts, or decoding

### Requirement: Separate source attestation from semantic correctness
The system SHALL publish new diagnosis artifacts that use `source_attested_exact` semantics and treat historical `trusted_provenance` only as a deprecated compatibility alias.

#### Scenario: Source attested exact is source-only
- **WHEN** a historical diagnostic has exact unique trusted provenance and valid span/hash/roundtrip evidence
- **THEN** new diagnosis artifacts may map it to `source_attested_exact=true`
- **AND** `semantic_correctness` MUST remain `unknown` in online-style semantics, `execution_eligible` MUST be `false`, and gold correctness MUST appear only in offline diagnosis artifacts

#### Scenario: Historical sidecars are not overwritten
- **WHEN** diagnosis writes sidecar v2 semantics or compatibility mappings
- **THEN** historical prediction sidecars, prediction files, evaluation audits, and frozen reports remain unchanged
- **AND** `trusted_provenance` MUST NOT be introduced as a runtime decision input

### Requirement: Classify source-attested-but-gold-mismatch cases
The system SHALL generate a public-safe case ledger for every source-attested-but-gold-mismatch event.

#### Scenario: Case ledger records required fields
- **WHEN** a source-attested exact event is not gold-correct
- **THEN** the ledger records challenge id, adapter role, task type, route, slot path, condition tags, predicted value, gold value, source span offsets, primary mechanism, secondary mechanisms, online detectability, offline gold requirement, deterministic mitigation possibility, task-level semantic-check requirement, scope policy implication, and a sanitized example
- **AND** it MUST NOT include private paths, raw private logs, checkpoint data, adapter weights, unreleased private corpus rows, or repaired predictions

#### Scenario: Mechanism taxonomy is deterministic
- **WHEN** mismatch cases are classified
- **THEN** each case receives exactly one primary mechanism from the approved taxonomy, including wrong entity, source-absent substitution, normalization-equivalence collision, overlong source span, underspecified partial span, wrong slot or scope, duplicate context disambiguation failure, generated value mismatch, challenge fixture or gold ambiguity, technical span attestation failure, or unclassified semantic mismatch

### Requirement: Detect normalized-equivalent collisions
The system SHALL audit raw-exact source-attested events for normalized-equivalent collision risk without enabling normalized trusted provenance.

#### Scenario: Raw exact unique but normalized-equivalent ambiguous
- **WHEN** a predicted value has one raw exact source span but more than one normalized-equivalent candidate span in the same source input
- **THEN** the diagnosis downgrades that event to `AMBIGUOUS_NORMALIZATION_COLLISION`
- **AND** `source_attested_exact=false`, `execution_eligible=false`, and normalized provenance remains candidate-only

#### Scenario: Collision detector covers bounded punctuation cases
- **WHEN** the detector evaluates examples such as `A/B` versus `AB`, `1.2` versus `12`, `C++` versus `C`, `v1.2` versus `v12`, URL punctuation, or email punctuation
- **THEN** it reports the triggering normalization rule and fails closed on non-reversible or overlapping ambiguous mappings

### Requirement: Review per-scope observe-only suitability
The system SHALL recompute per-scope mismatch risk and propose policy-v2 status for each enabled copy-shadow scope without modifying policy v1.

#### Scenario: Per-scope risk review is published
- **WHEN** diagnosis completes
- **THEN** the report includes source-attested count, gold-correct count/rate, gold-mismatch count/rate, source-absent substitution count, normalization collision count, partial or overlong count, wrong entity count, adapter role distribution, condition tag distribution, and proposed policy-v2 status for `search:search_web:query`, `form_fill:fill_form:field`, and `extract:extract_page:target`

#### Scenario: Form fill field gets explicit review
- **WHEN** the `form_fill:fill_form:field` scope is reviewed
- **THEN** the report evaluates whether the field slot is a field name, field value, DOM/schema resolver problem, or text-copy problem
- **AND** any future disable/limited-observe recommendation remains a proposal only

### Requirement: Publish compact false-trust diagnosis evidence
The system SHALL publish a bounded public-safe evidence bundle and concise truth-surface updates.

#### Scenario: Evidence bundle surface
- **WHEN** diagnosis succeeds
- **THEN** `reports/public-sample/copy-shadow-false-trust-diagnosis/` contains at most `summary.md`, `summary.json`, `false-trust-case-ledger.jsonl`, `per-scope-risk-review.json`, `normalization-collision-audit.json`, `sidecar-v2-semantics.md`, `recommended-next-change.md`, and `blocked.json` only when blocked
- **AND** it MUST NOT create per-mechanism subdirectories

#### Scenario: Documentation and truth surfaces stay bounded
- **WHEN** docs and truth surfaces are updated
- **THEN** they state that source attestation is not semantic correctness, not execution eligibility, not runtime enforcement, not model improvement, and not production or safety readiness
- **AND** they report the final decision label, per-scope proposal, unique next change, and no-training/no-enforcement boundaries

### Requirement: Emit conservative decision and next change
The system SHALL select exactly one false-trust diagnosis decision label and one next-change recommendation.

#### Scenario: Policy v2 review ready
- **WHEN** every mismatch case is classified, technical attestation false accept is zero, all normalization collision cases are downgraded, action/normalized attested count is zero, execution eligible count is zero, sidecar semantics are source-only, at least one scope remains observe-enabled, and no policy/runtime mutation occurred
- **THEN** the decision MAY be `SOURCE_ATTESTATION_SEMANTICS_HARDENED_POLICY_V2_REVIEW_READY`
- **AND** the only recommended next change MUST be `review-and-freeze-copy-shadow-policy-v2-before-naturalistic-challenge`

#### Scenario: Scope reduction required
- **WHEN** semantics are hardened but one or more enabled scopes should be disabled before further integration
- **THEN** the decision MUST be `SOURCE_ATTESTATION_HARDENED_SCOPE_REDUCTION_REQUIRED`
- **AND** the only recommended next change MUST be `design-copy-shadow-scope-policy-v2`

#### Scenario: No further integration
- **WHEN** all enabled scopes remain too weak for useful observe-only integration
- **THEN** the decision MUST be `COPY_SHADOW_OBSERVE_ONLY_NO_FURTHER_INTEGRATION`
- **AND** no policy v2 deployment, challenge v2, enforcement, training, action enablement, or normalized trusted provenance may be recommended
