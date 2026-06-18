## ADDED Requirements

### Requirement: Select scaled residual remediation target
The system SHALL publish public-safe target-selection evidence that chooses a
first remediation target from the scaled residual-cluster inspection without
changing model outputs, data, prompts, or evaluator semantics.

#### Scenario: Select target from scaled cluster inspection
- **WHEN** scaled residual-cluster inspection evidence exists for
  `public-sample-20260617T152259Z`
- **THEN** the target-selection evidence MUST read that cluster-inspection
  artifact and record the source manifest id, strict metrics, cluster count,
  residual row count, source residual field count, selected cluster, selected
  field path, selected rationale, deferred high-ranked clusters, and
  recommended next OpenSpec phase

#### Scenario: Preserve diagnosis-only boundaries
- **WHEN** scaled residual target-selection evidence is generated
- **THEN** it MUST state that no A100 job, training, prediction rerun, data
  mutation, data materialization, prompt change, evaluator relaxation,
  semantic-equivalence scoring, slot normalization, prediction repair, DPO/GRPO
  run, adapter release, checkpoint release, production-readiness claim, or
  live-browser benchmark claim was performed
- **AND** `contract_exact_match` and strict `slot_f1` MUST remain authoritative
  while `slot_f1_soft` remains diagnostic only

#### Scenario: Defer safety-sensitive targets explicitly
- **WHEN** a high-ranked blocked-payment residual cluster is not selected first
- **THEN** the target-selection evidence MUST record that the blocked-payment
  cluster is deferred to a dedicated safety boundary phase rather than treated
  as solved

#### Scenario: Recommend next phase only
- **WHEN** the selected target is recorded
- **THEN** the evidence MAY recommend a later OpenSpec phase for candidate
  design, policy review, data materialization, or training readiness
- **AND** it MUST NOT materialize data, launch training, change evaluator
  behavior, or claim model recovery in this phase

#### Scenario: Validate public-safe target-selection artifacts
- **WHEN** scaled residual target-selection artifacts, docs, Human Brief HTML,
  or archive files are prepared for commit
- **THEN** validation MUST reject raw private rows, absolute local paths,
  private remote paths, host details, SSH details, raw logs, tokens, secrets,
  private override configs, caches, checkpoints, adapters, and private corpus
  rows
