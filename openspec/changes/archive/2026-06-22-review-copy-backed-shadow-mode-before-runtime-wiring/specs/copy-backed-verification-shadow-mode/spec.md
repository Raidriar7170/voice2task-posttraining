## ADDED Requirements

### Requirement: Review shadow interface before prediction hook
The system SHALL review and harden the copy-backed shadow interface before any prediction-pipeline shadow hook is proposed.

#### Scenario: Review input boundary passes
- **WHEN** the review replay is generated
- **THEN** it uses only the current recovered raw inputs, the completed copy-backed verification slice, the previous shadow-mode sidecar evidence, the frozen scope policy, local code, docs, and OpenSpec artifacts
- **AND** it does not read or mutate runtime browser state, model checkpoints, private logs, training data, adapters, evaluator logic, predictions, gold rows, or downstream runtime behavior beyond the already public-safe recovered inputs

#### Scenario: Review input boundary blocks invalid input
- **WHEN** required source artifacts are missing or incompatible
- **THEN** the review writes `blocked.json` with `decision=SHADOW_REVIEW_BLOCKED_INVALID_INPUT`
- **AND** it MUST NOT write success summaries, sidecars, audits, hook recommendations, or runtime claims

### Requirement: Freeze copy-backed scope policy v1
The system SHALL freeze the copy-backed shadow review scope with a hash-validated policy artifact.

#### Scenario: Frozen policy is valid
- **WHEN** the review loads the scope policy
- **THEN** `policy_id` is `copy-backed-scope-policy-v1`, `action_enabled=false`, `normalized_trusted=false`, and enabled triples are exactly `search:search_web:query`, `form_fill:fill_form:field`, and `extract:extract_page:target`
- **AND** the report records the policy version, evidence hash, policy hash, enabled triples, disabled triples, action exclusion, and normalized-trusted exclusion

#### Scenario: Policy drift blocks review
- **WHEN** the policy hash, enabled triples, action flag, or normalized-trusted flag drifts
- **THEN** the review writes `blocked.json` with `decision=SHADOW_REVIEW_BLOCKED_POLICY_DRIFT`
- **AND** it MUST NOT produce a ready interface label

### Requirement: Split online sidecar from offline evaluation audit
The system SHALL separate the online shadow sidecar surface from offline gold/evaluator audit evidence.

#### Scenario: Online sidecar has no gold dependency
- **WHEN** an online shadow sidecar is generated
- **THEN** the generation function accepts no gold/evaluator argument and the sidecar contains no `gold`, `correct`, evaluator-score, or model-quality fields
- **AND** trusted/candidate provenance is derived only from input text, prediction contract, policy, verifier output, request/sample identity, and hashes

#### Scenario: Evaluation audit joins gold offline
- **WHEN** the offline audit is generated
- **THEN** it joins the online sidecar to gold/evaluator evidence in a separate function and writes correctness fields only to `evaluation-audits.jsonl`
- **AND** audit results MUST NOT mutate online sidecars, predictions, gold files, evaluator inputs, runtime decisions, or V1 metrics

### Requirement: Gate trusted provenance on exact unique span validation
The system SHALL trust only exact unique source spans that pass full validation.

#### Scenario: Exact unique trusted
- **WHEN** an enabled eligible slot is `VERIFIED_EXACT_UNIQUE` with `match_kind=exact`, one candidate span, a valid source hash, valid offsets, matching current input hash, and exact back-slice equality
- **THEN** the sidecar MAY set `trusted_provenance=true`

#### Scenario: Normalized remains candidate-only
- **WHEN** an enabled eligible slot is `VERIFIED_NORMALIZED_UNIQUE`
- **THEN** the sidecar MUST set `trusted_provenance=false`, `candidate_provenance=true`, and record the normalization rule id
- **AND** normalized verification MUST NOT be counted as trusted provenance

#### Scenario: Disabled scopes never trust
- **WHEN** a slot is out of the frozen policy scope, including `action`
- **THEN** the sidecar MUST set `policy_enabled=false`, `trusted_provenance=false`, and `candidate_provenance=false` even if text-span lookup could find the value

### Requirement: Publish review metrics, per-scope breakdowns, and latency evidence
The system SHALL publish a bounded review bundle with explicit denominators and local CPU latency evidence.

#### Scenario: Metrics use explicit denominators
- **WHEN** the review summary is generated
- **THEN** it reports total slot event count, out-of-scope count/rate over total, eligible slot event count, trusted exact count/rate over eligible, normalized candidate count/rate over eligible, eligible verification failure count/rate over eligible, global non-verified count/rate over total, trusted-exact gold correctness counts/rates over trusted exact, false accepts, silent fallbacks, contract mutation count, runtime decision delta count, and V1 evaluator metric deltas

#### Scenario: Per-scope and latency evidence are present
- **WHEN** review artifacts are written
- **THEN** they include per-scope metrics for each enabled triple by split, run role, task type, route, and slot path, plus a local CPU microbenchmark for policy lookup, exact unique span lookup, full span validation, and sidecar serialization
- **AND** latency evidence MUST NOT include hostnames, private IPs, SSH details, or production SLO claims

### Requirement: Decide bounded next step without runtime claims
The system SHALL emit exactly one bounded review decision and next change recommendation.

#### Scenario: Ready for prediction hook only
- **WHEN** online sidecars have no gold dependency, offline audits are isolated, trusted provenance is exact-only, normalized trusted count is zero, action trusted count is zero, false accepts and silent fallbacks are zero, contract mutation and runtime decision deltas are zero, V1 metric deltas are zero, deterministic replay is 1.0, policy hash is fixed, per-scope metrics are complete, and leak scan is clean
- **THEN** the decision MAY be `SHADOW_INTERFACE_READY_FOR_PREDICTION_HOOK`
- **AND** the next change MUST be `integrate-copy-backed-verification-prediction-shadow-hook`, still with no runtime enforcement

#### Scenario: Scope limitations are separated
- **WHEN** interface safety gates pass but per-scope evidence shows high mismatch, not-found, or ambiguity risk
- **THEN** the decision MAY be `SHADOW_INTERFACE_READY_WITH_SCOPE_LIMITATIONS`
- **AND** the next change MUST be `refine-shadow-hook-scope-before-integration`

#### Scenario: Unsafe interface is not ready
- **WHEN** online sidecars depend on gold, normalized provenance is trusted, the trusted-span validator is incomplete, false accepts appear, action is enabled, runtime behavior changes, evaluator behavior changes, policy is unfrozen, or evidence is incomplete
- **THEN** the decision MUST be `SHADOW_INTERFACE_NOT_READY`, `SHADOW_REVIEW_BLOCKED_INVALID_INPUT`, or `SHADOW_REVIEW_BLOCKED_POLICY_DRIFT`
- **AND** the report MUST NOT recommend runtime enforcement, action enablement, training, evaluator changes, prediction repair, model-quality claims, or production readiness
