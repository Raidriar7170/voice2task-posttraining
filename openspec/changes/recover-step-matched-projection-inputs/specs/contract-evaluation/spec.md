## ADDED Requirements

### Requirement: Retain row-level prediction inputs for reproducible evaluation
The system SHALL provide a minimal retention surface for future prediction runs
used as evaluation or projection inputs.

#### Scenario: Retain row-level prediction and gold artifacts
- **WHEN** a prediction run produces public-safe evaluation evidence
- **THEN** the system MUST be able to retain row-level `predictions.jsonl`,
  `gold.jsonl`, an artifact manifest, config hash, prompt hash, evaluator hash,
  and aggregate metric reproduction metadata without changing model output or
  evaluator logic

#### Scenario: Retention requires stable sample IDs
- **WHEN** retained prediction and gold rows are written
- **THEN** each row MUST include a stable sample ID and MUST NOT rely on file
  line number as the only alignment key

#### Scenario: Retention remains public-safe
- **WHEN** retained artifacts are prepared for commit
- **THEN** validation MUST reject absolute local paths, A100 paths, SSH aliases,
  IP addresses, hostnames, tokens, secrets, private adapter paths, checkpoint
  contents, private raw logs, and private corpus rows

### Requirement: Use retained inputs for later projection only after metric reproduction
The system SHALL allow retained raw inputs to feed later Contract V2 projection
only after boundary and metric reproduction checks pass.

#### Scenario: Projection inputs become ready
- **WHEN** recovered or retained raw inputs pass boundary checks and reproduce
  committed aggregate metrics
- **THEN** the system MAY set `projection_inputs_ready=true`
- **AND** it MAY recommend `rerun-contract-v2-projection-with-recovered-inputs`
  as a later separate change

#### Scenario: Projection inputs remain blocked
- **WHEN** recovered or retained raw inputs fail boundary checks or metric
  reproduction
- **THEN** `projection_inputs_ready` MUST remain false
- **AND** Contract V2 projection MUST NOT run in the same phase
