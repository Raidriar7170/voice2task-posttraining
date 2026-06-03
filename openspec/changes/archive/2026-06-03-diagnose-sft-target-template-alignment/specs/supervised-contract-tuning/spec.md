## ADDED Requirements

### Requirement: Diagnose SFT target and template alignment
The system SHALL provide a public-safe local diagnostic for SFT target rendering, assistant target span evidence, label-mask evidence boundaries, chat-template policy, and adapter/base metadata alignment before another private A100 rerun is interpreted.

#### Scenario: Compare training and prediction rendering
- **WHEN** the diagnostic runs on committed public-sample SFT rows with SFT and prediction configs
- **THEN** it MUST render SFT training text and prediction prompt text for matching rows, record whether they share the same system/user prefix, record whether the prediction prompt excludes the gold target contract, and record whether the assistant target contract appears only in the training text

#### Scenario: Report assistant target and label-mask evidence separately
- **WHEN** the diagnostic can identify the assistant contract target span in rendered training text
- **THEN** it MUST report structural target-span evidence separately from true label-mask evidence and MUST mark true label-mask evidence as unavailable unless labels from the inspected training path are available

#### Scenario: Record chat-template policy evidence
- **WHEN** tokenizer chat-template rendering is unavailable or intentionally not loaded for local validation
- **THEN** the diagnostic MUST record deterministic fallback rendering, the shared formatting policy, and tokenizer-template absence as an evidence gap rather than inferring tokenizer-specific training behavior

#### Scenario: Compare adapter and base metadata safely
- **WHEN** prior prediction metadata and public config templates are provided
- **THEN** the diagnostic MUST compare public-safe base model placeholder status, model source, stack, prediction split, adapter gate status, and formatting-policy fields without exposing private adapter paths, private base-model paths, host details, or raw logs

### Requirement: Bound SFT alignment interpretation
The system SHALL prevent SFT alignment diagnostics from being interpreted as a model-quality, release, or rerun-success claim.

#### Scenario: Describe diagnostic result
- **WHEN** SFT target/template alignment evidence is reported
- **THEN** the report MUST state that the diagnostic does not run private prediction, does not retrain, does not repair outputs, and does not prove checkpoint release, adapter release, dev/test generalization, production readiness, or live-browser benchmark improvement
