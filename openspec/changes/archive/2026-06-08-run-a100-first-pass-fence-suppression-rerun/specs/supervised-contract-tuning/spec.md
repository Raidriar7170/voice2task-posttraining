## ADDED Requirements

### Requirement: Run A100 first-pass fence-suppression rerun
The system SHALL support a bounded, explicitly authorized A100 prediction-only train-split rerun after first-pass Markdown fence suppression while keeping all private runtime artifacts outside git.

#### Scenario: Launch prediction-only rerun with approved private runtime
- **WHEN** a developer launches the rerun with A100 authorization, a repo-external private override, an existing private adapter path, an approved private output root represented in public artifacts as `<a100_project_root>`, and a safe idle GPU selected without interrupting other users
- **THEN** the system MUST use `prediction_split=train`, `overfit_diagnostic=true`, `generalization_claim=false`, current first-pass Markdown fence suppression decoding policy, strict raw/retry parsing, and public-sample train rows
- **AND** it MUST write remote outputs only under the approved private project root

#### Scenario: Preserve strict prediction behavior
- **WHEN** model outputs contain Markdown fences, prose wrappers, malformed JSON, or contract-like fragments
- **THEN** the prediction artifact and sidecars MUST preserve sanitized failure evidence without stripping fences, extracting embedded JSON, replacing predictions with fixtures/gold/rule outputs, or changing schema guard semantics

#### Scenario: Keep private A100 artifacts private
- **WHEN** the rerun completes or fails
- **THEN** raw logs, checkpoints, adapters, caches, private overrides, host details, SSH details, private paths, tokens, and private corpus rows MUST remain outside committed artifacts
