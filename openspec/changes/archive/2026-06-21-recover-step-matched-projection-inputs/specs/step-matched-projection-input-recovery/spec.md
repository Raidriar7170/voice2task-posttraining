## ADDED Requirements

### Requirement: Recover step-matched projection inputs
The system SHALL recover the raw row-level Control/Treatment dev/test
predictions and aligned dev/test gold contracts for the latest step-matched
canonical-slot ablation, or fail closed with a bounded decision label.

#### Scenario: Existing raw artifacts are recovered
- **WHEN** original step-matched raw predictions and gold contracts are found
- **THEN** the system MUST verify run identity, config hash, manifest ID, sample
  IDs, split, gold hashes, and adapter identity before copying sanitized
  artifacts to the public recovery output directory

#### Scenario: Recovery blocks when original artifacts are unavailable
- **WHEN** original step-matched prediction artifacts are missing or any fresh
  adapter identity evidence is missing, overwritten, or identity-unverifiable
- **THEN** the system MUST write `blocked.json` with
  `decision=RECOVERY_BLOCKED_ADAPTER_UNAVAILABLE`
- **AND** it MUST NOT retrain, rebuild adapters, run prediction reproduction,
  use old adapters, infer predictions from metrics, or repair predictions

### Requirement: Write public-safe raw-input artifacts
The system SHALL write recovered or blocked evidence under
`reports/public-sample/step-matched-canonical-slot-ablation/raw-inputs/`.

#### Scenario: Write required files
- **WHEN** recovery completes or blocks
- **THEN** the output directory MUST include `artifact-manifest.json`,
  `boundary-verification.json`, `metric-reproduction.json`,
  `recovery-summary.md`, and `blocked.json` only when blocked

#### Scenario: Write row-level prediction schema
- **WHEN** prediction artifacts are recovered
- **THEN** each prediction row MUST include stable `sample_id`, split,
  input hash, gold contract, prediction contract or parse failure state,
  public-safe raw model output summary, run role, run ID, manifest ID, config
  hash, prompt hash, and model output hash

#### Scenario: Write row-level gold schema
- **WHEN** gold artifacts are written
- **THEN** each gold row MUST include stable `sample_id`, split, input hash,
  gold contract, gold hash, and manifest ID

### Requirement: Validate recovery boundaries
The system SHALL validate that recovered inputs match the frozen held-out
boundary and the step-matched experiment identity.

#### Scenario: Validate sample and gold alignment
- **WHEN** boundary verification runs
- **THEN** it MUST verify dev/test row counts, unique sample IDs, matching
  Control/Treatment/Gold sample ID sets, no dev/test ID overlap, matching input
  hashes, matching Control/Treatment gold contracts, and matching frozen gold
  hashes

#### Scenario: Validate experiment identity
- **WHEN** boundary verification runs
- **THEN** it MUST verify corresponding fresh Control/Treatment adapter
  identities, config match, prompt match, evaluator match, and that old adapter
  or old-manifest predictions were not used

#### Scenario: Boundary mismatch fails closed
- **WHEN** any critical boundary check fails
- **THEN** `comparison_allowed` MUST be false
- **AND** the decision label MUST be `RECOVERY_INVALID_BOUNDARY_MISMATCH`

### Requirement: Reproduce committed step-matched metrics
The system SHALL recompute committed aggregate metrics from recovered row-level
artifacts using the existing evaluator without changing evaluator semantics.

#### Scenario: Metrics reproduce within tolerance
- **WHEN** all required metrics reproduce within absolute tolerance no greater
  than `1e-9`
- **THEN** `metric_reproduction_status` MUST be `reproduced`
- **AND** `projection_inputs_ready` MAY be true only if all boundary checks also
  passed

#### Scenario: Metric mismatch fails closed
- **WHEN** any required metric cannot be reproduced within tolerance
- **THEN** the system MUST write the expected value, reproduced value, absolute
  delta, tolerance, and `passed=false`
- **AND** the decision label MUST be `RECOVERY_INVALID_METRIC_MISMATCH`
- **AND** it MUST NOT modify old metrics or run Contract V2 projection

### Requirement: Emit bounded recovery decision
The system SHALL emit exactly one approved recovery decision label.

#### Scenario: Successful recovery from original artifacts
- **WHEN** original outputs are found, boundary verification passes, and metrics
  reproduce
- **THEN** the decision label MUST be `RECOVERED_FROM_EXISTING_ARTIFACTS`
- **AND** `projection_inputs_ready` MUST be true

#### Scenario: Failed recovery labels
- **WHEN** recovery cannot proceed or recovered artifacts are invalid
- **THEN** the decision label MUST be one of
  `RECOVERY_BLOCKED_ADAPTER_UNAVAILABLE`,
  `RECOVERY_INVALID_BOUNDARY_MISMATCH`, or
  `RECOVERY_INVALID_METRIC_MISMATCH`
- **AND** `projection_inputs_ready` MUST be false

### Requirement: Preserve phase non-goals
The system SHALL keep recovery separate from training, model-quality claims, and
Contract V2 projection execution.

#### Scenario: Recovery does not expand scope
- **WHEN** this phase runs
- **THEN** it MUST NOT train, run DPO or GRPO, continue training, modify the
  base model, LoRA config, prompt template, decoding parameters, evaluator,
  normalization, gold contracts, splits, data, prediction repair, LLM judge,
  semantic-equivalence scoring, Contract V2 implementation, or Contract V2
  projection
