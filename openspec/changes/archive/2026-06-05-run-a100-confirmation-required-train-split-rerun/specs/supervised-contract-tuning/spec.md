## ADDED Requirements

### Requirement: Run authorized A100 confirmation-required train-split rerun
The system SHALL support a bounded, explicitly authorized A100 train-split prediction rerun after local confirmation-required prompt repair while keeping all private runtime artifacts outside committed files.

#### Scenario: Launch confirmation-required rerun with explicit authorization
- **WHEN** a developer launches the rerun with explicit prediction opt-in, a repo-external private override, and an idle A100 GPU under the approved private project root
- **THEN** the system MUST use `prediction_split=train`, `overfit_diagnostic=true`, `generalization_claim=false`, `schema_retry_enabled=true`, and the current shared confirmation-required prompt without starting SFT, DPO, or GRPO training

#### Scenario: Reuse existing private adapter for prediction only
- **WHEN** the confirmation-required rerun is executed
- **THEN** it MUST use the existing private train-split adapter and MUST NOT create, publish, or commit checkpoints, adapters, raw logs, caches, private overrides, host details, SSH details, tokens, or private paths

#### Scenario: Preserve invalid model output
- **WHEN** raw or retry attempts omit `confirmation_required`, include Markdown/prose wrappers, or otherwise fail strict Browser Task Contract validation
- **THEN** the prediction artifact and sidecars MUST preserve sanitized failure evidence without filling `confirmation_required`, replacing outputs with fixtures, accepting JSON fragments as valid, or using gold-contract repair

#### Scenario: Reject unresolved or unsafe private configuration
- **WHEN** prediction is launched without explicit opt-in, with unresolved template paths, without a repo-external private override, without an approved output root, or without a configured private adapter path
- **THEN** prediction MUST fail closed or remain blocked without producing misleading fixture-mode evidence
