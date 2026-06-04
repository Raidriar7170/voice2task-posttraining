## ADDED Requirements

### Requirement: Run authorized A100 strict-retry train-split prediction rerun
The system SHALL support a bounded, explicitly authorized A100 prediction-only train-split rerun after constrained decoding repair while keeping all private runtime artifacts outside committed files.

#### Scenario: Launch strict-retry prediction rerun
- **WHEN** a developer launches the rerun with explicit private-prediction opt-in, a repo-external private override, an existing private adapter path, and an idle A100 GPU under the approved private project root
- **THEN** the system MUST run only public-sample train-split prediction through the current strict retry/canonical Browser Task Contract prediction path

#### Scenario: Predict with strict retry and schema guard
- **WHEN** the private adapter is used for train-split prediction
- **THEN** the system MUST use `prediction_split=train`, `overfit_diagnostic=true`, `generalization_claim=false`, `schema_retry_enabled=true`, and the current strict whole-string retry JSON parser

#### Scenario: Preserve observed failures
- **WHEN** raw or retry prediction attempts are generated
- **THEN** the system MUST preserve raw attempt schema validity, retry attempt schema validity, validated output source, final prediction status, and invalid outputs without replacing them with fixture-mode, rule-baseline, gold-contract, or locally coerced predictions

#### Scenario: Keep private adapter artifacts private
- **WHEN** the prediction rerun completes or fails
- **THEN** raw logs, checkpoints, adapters, model caches, private overrides, host details, SSH details, private paths, tokens, and private corpus rows MUST remain outside committed artifacts
