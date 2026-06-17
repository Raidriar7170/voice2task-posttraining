## ADDED Requirements

### Requirement: Retry scaled-manifest A100 prediction baseline after recovery
The system SHALL produce public-safe observed-or-blocked evidence when retrying
the scaled public-sample prediction-only baseline after an A100 connectivity
recovery.

#### Scenario: Observed retry writes strict prediction evidence
- **WHEN** the A100 development machine is reachable, an approved GPU is safe to
  use, the existing private `a100-current-train-split-sft-retry` adapter is
  available, and dev/test predictions are generated for
  `public-sample-20260617T152259Z`
- **THEN** the committed evidence MUST record `run_status="observed"`, the
  target manifest id, dev/test prediction counts, strict contract ladder
  metrics, prediction metadata, and a comparison boundary marking direct
  improvement/regression comparison invalid
- **AND** the evidence MUST state that this was prediction-only and that no
  training, data mutation, evaluator relaxation, slot normalization, prediction
  repair, adapter release, checkpoint release, production-readiness claim, or
  live-browser benchmark claim was performed

#### Scenario: Unsafe retry fails closed
- **WHEN** the A100 development machine, approved GPU placement, remote
  environment, source adapter, or prediction command cannot be verified safely
- **THEN** the committed evidence MUST record a blocked status and blocked
  reason without writing fabricated predictions, fabricated metrics, or a model
  recovery claim
- **AND** the evidence MUST preserve the previous blocked baseline as historical
  evidence rather than overwriting it

#### Scenario: Public artifacts remain sanitized
- **WHEN** retry evidence, status docs, Human Brief HTML, or OpenSpec archive
  artifacts are prepared for commit
- **THEN** validation MUST reject raw logs, host details, SSH details, tokens,
  secrets, absolute local paths, private remote paths, private override configs,
  caches, checkpoints, adapters, and private corpus rows
