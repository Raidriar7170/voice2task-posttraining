## ADDED Requirements

### Requirement: Run current canonical-boundary prediction baseline
The system SHALL publish public-safe observed-or-blocked prediction-only
evidence for the current canonical slot-boundary merged formal public sample
manifest.

#### Scenario: Observed current-boundary baseline writes strict evidence
- **WHEN** the A100 development machine is reachable, an idle GPU can be chosen
  safely, the existing private `a100-current-train-split-sft-retry` adapter is
  available, and dev/test predictions are generated for
  `public-sample-20260619T090925Z`
- **THEN** committed evidence MUST record `run_status="observed"`, target
  manifest id `public-sample-20260619T090925Z`, dev/test prediction counts,
  strict contract ladder metrics, prediction metadata, source adapter lineage,
  and a comparison boundary marking direct old/new improvement or regression
  comparison invalid
- **AND** committed evidence MUST state that this phase is prediction-only and
  does not train, mutate data, change prompts, relax evaluator semantics,
  normalize slots, repair predictions, release adapters or checkpoints, claim
  production readiness, or claim live-browser benchmark improvement

#### Scenario: Unsafe or unavailable baseline fails closed
- **WHEN** A100 connectivity, safe GPU placement, remote dependencies, the
  private adapter, or the prediction command cannot be verified safely
- **THEN** committed evidence MUST record a blocked status and blocked reason
  without writing fabricated predictions, fabricated metrics, or model recovery
  claims
- **AND** the latest prior model evidence MUST remain clearly labeled as
  historical evidence for an older manifest boundary

#### Scenario: Public artifacts stay sanitized
- **WHEN** current-boundary baseline evidence, status docs, Human Brief HTML, or
  OpenSpec archive artifacts are prepared for commit
- **THEN** validation MUST reject raw private rows, absolute local paths,
  private remote paths, host details, SSH details, tokens, secrets, raw logs,
  private override configs, caches, checkpoints, adapters, and private corpus
  rows
- **AND** public summaries MUST keep strict `contract_exact_match` and strict
  `slot_f1` authoritative while labeling `slot_f1_soft` diagnostic only
