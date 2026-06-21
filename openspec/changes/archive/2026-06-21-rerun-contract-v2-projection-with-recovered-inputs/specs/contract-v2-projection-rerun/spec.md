## ADDED Requirements

### Requirement: Verify recovered projection input boundary
The system SHALL verify recovered step-matched raw inputs before computing
Contract V2 projection metrics.

#### Scenario: Accept recovered metric reproduction evidence
- **WHEN** the rerun reads
  `reports/public-sample/step-matched-canonical-slot-ablation/raw-inputs/artifact-manifest.json`
- **THEN** it MUST require `projection_inputs_ready=true`
- **AND** it MUST accept `metric_reproduction_status` values that mean recovered
  metrics reproduced successfully, including the current value `reproduced`
- **AND** it MUST record the accepted status in `source-boundary.json`

#### Scenario: Reject invalid recovered boundary
- **WHEN** row counts, sample id sets, Control/Treatment/Gold sets, dev/test
  disjointness, frozen gold hashes, config hashes, prompt hash, evaluator hash,
  recovery method, or sanitization status do not match the recovered manifest
- **THEN** it MUST write `blocked.json`
- **AND** it MUST set the boundary decision to
  `PROJECTION_INVALID_INPUT_BOUNDARY`
- **AND** it MUST stop without computing projection metrics

### Requirement: Project parsed V1 contracts into field-limited V2 Core
The system SHALL project valid V1 contracts into deterministic V2 Core objects
that contain only core executable fields.

#### Scenario: V2 Core contains only approved fields
- **WHEN** a V1 contract is projected
- **THEN** the V2 Core object MUST contain exactly `task_type`, `route`,
  `safety`, `confirmation_required`, and `slots`
- **AND** it MUST omit `normalized_command`, `language`, and `contract_version`
- **AND** it MUST reject fields such as `allowed_actions`, `success_criteria`,
  `policy_tags`, and `runtime_hints`

#### Scenario: Projection uses parsed contract fields
- **WHEN** recovered prediction rows contain both `prediction_contract` and
  `raw_model_output`
- **THEN** projection MUST use `prediction_contract` as the primary prediction
  input
- **AND** it MUST NOT parse or score `raw_model_output` as token-level decoded
  text

### Requirement: Build deterministic V2 envelopes
The system SHALL build experimental V2 envelopes from V2 Core using fixed
metadata and a deterministic display renderer.

#### Scenario: Envelope adds deterministic metadata
- **WHEN** a valid V2 Core object is converted to an envelope
- **THEN** the envelope MUST set `language="zh-CN"`
- **AND** it MUST set `contract_version="v2"`
- **AND** it MUST add `normalized_command` only from the deterministic renderer

#### Scenario: Envelope fails closed for unsupported renderer output
- **WHEN** the renderer cannot support a V2 Core object with bounded templates
- **THEN** envelope construction MUST return an unsupported result instead of a
  free-form generated command

### Requirement: Render normalized commands without reading old commands
The system SHALL provide a deterministic renderer that reads only V2 Core
fields and preserves slot values.

#### Scenario: Renderer ignores V1 normalized command
- **WHEN** two V1 contracts differ only in `normalized_command`
- **THEN** their projected V2 Core renderer outputs MUST be identical

#### Scenario: Renderer preserves distinct values
- **WHEN** core slots contain distinct cities, dates, prices, products, URLs,
  emails, field names, or field values
- **THEN** renderer output MUST NOT merge, substitute, normalize away, or
  collapse those values

#### Scenario: Renderer reports coverage
- **WHEN** the rerun completes
- **THEN** it MUST report supported rate, unsupported count, task-type
  coverage, unsupported reason distribution, public-safe examples, and
  deterministic roundtrip rate

### Requirement: Preserve offline-only projection boundaries
The system SHALL keep the rerun local, deterministic, and evidence-only.

#### Scenario: Rerun performs no model or data mutation work
- **WHEN** the rerun executes
- **THEN** it MUST NOT invoke A100, SSH, GPU jobs, model generation, training,
  DPO, GRPO, dataset mutation, split mutation, gold mutation, prompt mutation,
  evaluator relaxation, LLM judges, semantic-equivalence scoring, or prediction
  repair

#### Scenario: Rerun does not overwrite historical blocked evidence
- **WHEN** rerun artifacts are generated
- **THEN** they MUST be written under
  `reports/public-sample/contract-v2-projection/rerun-with-recovered-inputs/`
- **AND** historical root-level blocked projection evidence MUST remain
  preserved
