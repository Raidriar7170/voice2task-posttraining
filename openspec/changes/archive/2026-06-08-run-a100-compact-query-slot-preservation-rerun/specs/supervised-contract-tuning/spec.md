## ADDED Requirements

### Requirement: Run A100 compact query slot preservation rerun
The system SHALL support a bounded A100 prediction-only train-split rerun after compact query slot preservation repair while keeping private runtime artifacts outside git.

#### Scenario: Launch compact query slot preservation rerun
- **WHEN** a developer launches the rerun with A100 authorization, a repo-external private override, an existing private adapter path, an idle A100 GPU, and an approved private output root represented in public artifacts as `<a100_project_root>`
- **THEN** the rerun MUST use `prediction_split=train`, `overfit_diagnostic=true`, `generalization_claim=false`, the current public-sample manifest, and the current trained-adapter prediction prompt policy
- **AND** it MUST write sanitized predictions plus prompt snapshot, raw decoded summary, generation trace, prediction metadata, schema guard summary, metrics, and diagnosis artifacts suitable for public evidence

#### Scenario: Keep private A100 artifacts private
- **WHEN** the compact query slot preservation rerun completes or fails
- **THEN** raw logs, checkpoints, adapters, caches, private overrides, host details, SSH details, private paths, tokens, and private corpus rows MUST remain outside committed artifacts

#### Scenario: Preserve rerun outputs honestly
- **WHEN** the private adapter emits decomposed slots, invalid JSON, wrapper text, non-contract JSON, or any strict mismatch
- **THEN** the prediction artifact and sidecars MUST preserve sanitized model output and strict failure status without replacing it with fixture-mode, rule-baseline, normalized, repaired, or gold contracts
