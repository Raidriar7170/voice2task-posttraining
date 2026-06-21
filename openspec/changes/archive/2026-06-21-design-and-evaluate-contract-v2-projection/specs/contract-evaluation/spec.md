## ADDED Requirements

### Requirement: Publish Contract V2 projection ladder evidence
The system SHALL publish public-safe offline projection evidence for the latest
step-matched canonical-slot Control and Treatment dev/test predictions without
changing the existing V1 strict evaluator.

#### Scenario: Verify projection source boundary
- **WHEN** Contract V2 projection evaluation starts
- **THEN** it MUST read the latest committed step-matched canonical-slot
  ablation boundary verification, Control/Treatment dev/test predictions,
  Control/Treatment metrics, paired row analysis, family deltas, comparison,
  and decision artifacts
- **AND** it MUST verify dev/test sample ID equality, gold contract equality,
  prediction/gold alignability by stable sample ID, V1 schema source from code,
  and that no A100, SSH, adapter, or prediction generation is needed

#### Scenario: Fail closed on missing or unaligned inputs
- **WHEN** any required input is missing, stale, or cannot be aligned
- **THEN** the system MUST write blocked projection evidence with
  `decision_label=PROJECTION_BLOCKED_OR_INVALID`
- **AND** it MUST NOT fabricate predictions, metrics, or a follow-on design
  phase

#### Scenario: Compute projection ladder metrics
- **WHEN** Control/Treatment dev/test source inputs are aligned
- **THEN** the system MUST report L0 V1 full strict, L1 V1 without
  `normalized_command`, L2 V2 Core strict, and L3 V2 envelope validation
  metrics separately
- **AND** it MUST NOT overwrite, rename, or relax the existing V1 strict exact
  result

#### Scenario: Preserve executable and guardrail criteria
- **WHEN** V2 core executable pass rate is computed
- **THEN** it MUST still require correct task type, route, safety,
  confirmation, required slot keys, required slot values under current
  deterministic slot policy, and no unsafe downgrade

### Requirement: Analyze derived-field and core failure contribution
The system SHALL classify every V1 strict failure into bounded contribution
families that separate derived-field failures from core contract failures.

#### Scenario: Classify strict failures
- **WHEN** a row fails V1 strict exact
- **THEN** the system MUST classify it as one of
  `NORMALIZED_COMMAND_ONLY`, `METADATA_ONLY`, `DERIVED_FIELD_ONLY`,
  `CORE_SLOT_FAILURE`, `CORE_ROUTE_TASK_FAILURE`,
  `CORE_SAFETY_CONFIRMATION_FAILURE`, or `MIXED_CORE_FAILURE`

#### Scenario: Report contribution aggregates
- **WHEN** failure contribution analysis is generated
- **THEN** it MUST include Control/Treatment dev/test counts and proportions,
  top task families, top slot field paths, public-safe examples, eliminated
  V1 strict failure counts, and residual counts after projection

### Requirement: Compare projection counterfactuals conservatively
The system SHALL publish absolute deltas and paired bootstrap diagnostics for
projection metrics without claiming model improvement from field removal.

#### Scenario: Report counterfactual deltas
- **WHEN** projection metrics are available
- **THEN** the system MUST report `L1 exact - L0 exact`,
  `L2 exact - L0 exact`, `L2 exact - L1 exact`, and
  `V2 core executable pass - V1 executable pass`

#### Scenario: Run deterministic bootstrap
- **WHEN** paired bootstrap analysis is generated
- **THEN** it MUST use a fixed seed, record bootstrap iterations, and include
  exact pass delta, executable pass delta, and task-family-level delta

#### Scenario: Bound metric interpretation
- **WHEN** reports describe improved exact after removing derived fields
- **THEN** they MUST state that projection removes derived-field consistency
  burden and does not retrain, improve, or repair the model

### Requirement: Emit bounded projection decision
The system SHALL emit exactly one projection decision label from the approved
set and recommend at most one next bounded change.

#### Scenario: Proceed gate
- **WHEN** dev/test V2 core exact each improves by at least 0.08 over V1
  strict, derived-field-only failures are at least 20 percent of V1 strict
  failures, V2 core executable pass does not decline, safety and confirmation
  metrics do not decline, renderer support is at least 0.95, deterministic
  roundtrip is 1.0, and core slot failures no longer dominate
- **THEN** the decision label MUST be
  `PROCEED_TO_CONTRACT_V2_IMPLEMENTATION`
- **AND** the recommended next change MAY be
  `implement-contract-v2-core-and-postprocessor`

#### Scenario: Partial schema benefit
- **WHEN** exact improves but does not satisfy the proceed gate, only one split
  improves, renderer coverage is insufficient, or slot bottleneck remains
  visible
- **THEN** the decision label MUST be `PARTIAL_SCHEMA_BENEFIT`

#### Scenario: Slot bottleneck persists
- **WHEN** V2 core exact improves little, executable pass does not materially
  improve, slot failure remains dominant, and derived-field-only failure share
  is low
- **THEN** the decision label MUST be `SLOT_BOTTLENECK_PERSISTS`

#### Scenario: Projection blocked or invalid
- **WHEN** projection cannot be deterministic, policy is unclear, renderer
  coverage is too low for valid envelope evaluation, or source artifacts cannot
  be aligned
- **THEN** the decision label MUST be `PROJECTION_BLOCKED_OR_INVALID`

### Requirement: Keep projection reports public-safe
The system SHALL publish projection artifacts that are sanitized and explicit
about non-claims.

#### Scenario: Write required projection artifacts
- **WHEN** projection evaluation completes or blocks
- **THEN** it MUST write `source-boundary.json`, `projection-spec.md`,
  `projection-spec.json`, `field-policy.md`,
  `normalized-command-renderer-report.md`,
  `normalized-command-renderer-report.json`, per-arm/split projection metrics,
  `failure-contribution-analysis.json`, `failure-contribution-analysis.md`,
  `family-level-projection-deltas.json`, `bootstrap-analysis.json`,
  `decision.md`, `summary.md`, `summary.json`, and
  `recommended-next-change.md` under
  `reports/public-sample/contract-v2-projection/`

#### Scenario: Validate projection public safety
- **WHEN** projection artifacts, docs, Human Brief HTML, or OpenSpec archives
  are prepared for commit
- **THEN** validation MUST reject raw private rows, absolute local paths,
  private remote paths, private hostnames, IP addresses, SSH details, tokens,
  secrets, raw private logs, checkpoints, adapters, caches, and private corpus
  rows
