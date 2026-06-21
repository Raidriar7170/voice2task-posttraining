## ADDED Requirements

### Requirement: Publish recovered-input Contract V2 projection ladder evidence
The system SHALL publish public-safe recovered-input projection evidence for
Control and Treatment dev/test splits without changing V1 evaluator semantics.

#### Scenario: Compute separated projection ladder metrics
- **WHEN** recovered raw inputs pass boundary verification
- **THEN** the system MUST report original V1 strict metrics, L1 V1 without
  `normalized_command`, L2 V2 Core strict, and L3 V2 envelope evaluation
  metrics separately for Control and Treatment dev/test
- **AND** it MUST NOT name any L1, L2, or L3 metric
  `contract_exact_match_strict`

#### Scenario: Preserve V2 core executable criteria
- **WHEN** V2 Core executable pass is computed
- **THEN** it MUST require correct task type, route, safety, confirmation,
  required slot keys, required slot values under the current deterministic slot
  policy, no unsafe downgrade, and deterministic consumer shape

### Requirement: Classify recovered-input projection failures
The system SHALL classify every V1 strict failure into the approved recovered
projection contribution categories.

#### Scenario: Use approved contribution categories
- **WHEN** a row fails V1 strict exact match
- **THEN** it MUST be classified as exactly one of
  `NORMALIZED_COMMAND_ONLY`, `METADATA_ONLY`, `DERIVED_FIELD_ONLY`,
  `CORE_SLOT_FAILURE`, `CORE_ROUTE_TASK_FAILURE`,
  `CORE_SAFETY_CONFIRMATION_FAILURE`, `MIXED_CORE_FAILURE`, or
  `INVALID_OR_UNPARSEABLE`

#### Scenario: Report contribution aggregates
- **WHEN** contribution analysis is generated
- **THEN** it MUST include counts and proportions per arm/split, task-family
  distribution, top slot field paths, public-safe examples, eliminated V1
  strict failures, and remaining core failures

### Requirement: Compare recovered-input projection counterfactuals
The system SHALL publish conservative deltas and fixed-seed bootstrap
diagnostics for the recovered projection rerun.

#### Scenario: Report projection deltas
- **WHEN** projection metrics are available
- **THEN** the system MUST report `L1 exact - L0 exact`,
  `L2 exact - L0 exact`, `L2 exact - L1 exact`, and
  `V2 core executable pass - V1 executable pass` for Control and Treatment
  dev/test

#### Scenario: Run deterministic bootstrap
- **WHEN** bootstrap analysis is generated
- **THEN** it MUST use a fixed seed and record iterations, exact-pass delta
  confidence intervals, executable-pass delta confidence intervals, and
  family-level deltas

### Requirement: Emit recovered projection decision and non-claims
The system SHALL emit exactly one recovered projection decision label and
explicitly state claims that remain unsupported.

#### Scenario: Emit approved decision label
- **WHEN** the rerun completes or blocks
- **THEN** the decision label MUST be exactly one of
  `PROCEED_TO_CONTRACT_V2_IMPLEMENTATION`, `PARTIAL_SCHEMA_BENEFIT`,
  `SLOT_BOTTLENECK_PERSISTS`, or `PROJECTION_INVALID_OR_BLOCKED`
- **AND** it MUST recommend at most one next bounded change

#### Scenario: Answer required final questions
- **WHEN** summary artifacts are written
- **THEN** they MUST answer whether recovered step-matched contracts were used,
  normalized-command-only share, metadata-only share, derived-field-only share,
  V2 core exact improvement, V2 core executable improvement, slot bottleneck
  status, safety and confirmation retention, renderer coverage and
  deterministic roundtrip, whether formal Contract V2 is warranted, final
  decision label, recommended next change, and remaining non-claims

### Requirement: Keep recovered projection artifacts complete and public-safe
The system SHALL write the required rerun artifact set and validate public
safety.

#### Scenario: Write complete rerun artifact set
- **WHEN** projection completes
- **THEN** the rerun output directory MUST contain `source-boundary.json`,
  `projection-spec.md`, `projection-spec.json`, `field-policy.md`,
  `normalized-command-renderer-report.md`,
  `normalized-command-renderer-report.json`,
  `control/dev-projection-metrics.json`,
  `control/test-projection-metrics.json`,
  `treatment/dev-projection-metrics.json`,
  `treatment/test-projection-metrics.json`,
  `failure-contribution-analysis.json`,
  `failure-contribution-analysis.md`,
  `family-level-projection-deltas.json`, `bootstrap-analysis.json`,
  `decision.md`, `summary.md`, `summary.json`, and
  `recommended-next-change.md`

#### Scenario: Write blocked rerun artifact when needed
- **WHEN** source-boundary verification fails
- **THEN** the rerun output directory MUST contain `blocked.json`
- **AND** it MUST NOT fabricate metric artifacts

#### Scenario: Validate public safety
- **WHEN** rerun artifacts, documentation, or Human Brief HTML are prepared for
  commit
- **THEN** validation MUST reject raw private rows, absolute local paths,
  private remote paths, host details, SSH details, tokens, secrets, raw logs,
  checkpoints, adapters, caches, private corpus rows, and unsupported readiness
  claims
