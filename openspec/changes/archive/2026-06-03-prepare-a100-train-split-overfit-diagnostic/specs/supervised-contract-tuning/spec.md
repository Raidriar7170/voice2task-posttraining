## ADDED Requirements

### Requirement: Prepare train-split overfit diagnostic prediction exports
The system SHALL provide a public-safe preparation path for train-split overfit diagnostic prediction exports without launching private A100 execution from the local preparation phase.

#### Scenario: Configure train-split diagnostic prediction
- **WHEN** a developer prepares the diagnostic prediction config
- **THEN** the committed template MUST use `prediction_split=train`, mark `overfit_diagnostic=true`, keep private paths as placeholders, and require a private override before remote execution

#### Scenario: Record prompt and decoding sidecars
- **WHEN** trained-adapter prediction rows are generated for the diagnostic path
- **THEN** the system MUST be able to write public-safe prompt snapshot, sanitized raw decoded summary, and generation trace artifacts without changing the prediction values used for schema metrics

#### Scenario: Preserve raw failure evidence
- **WHEN** model output is schema-invalid, truncated, non-JSON, or contract-like but wrong
- **THEN** the prediction artifact and sidecars MUST preserve sanitized failure evidence without replacing it with fixture, rule-baseline, or gold contracts

### Requirement: Inspect SFT objective masking before overfit claims
The system SHALL expose an objective-inspection result for the SFT data path before train-split overfit results are interpreted as evidence that assistant contract targets were learned, and SHALL fail closed when real label evidence is unavailable.

#### Scenario: Report objective mask status
- **WHEN** objective inspection runs on a public-sample SFT row
- **THEN** the output MUST report prompt/system/user mask status and assistant contract loss status only when labels from the actual inspected training path are available, otherwise it MUST set those fields to null and report `dependency_unavailable`, `tokenizer_unavailable`, or `labels_unavailable`

#### Scenario: Bound objective interpretation
- **WHEN** objective inspection cannot prove assistant-only or completion-only loss
- **THEN** the overfit diagnostic MUST report that loss improvement alone is not proof of Browser Task Contract learning
