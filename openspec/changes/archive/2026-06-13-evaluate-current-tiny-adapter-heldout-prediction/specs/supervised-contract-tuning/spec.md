## ADDED Requirements

### Requirement: Run current-manifest tiny adapter held-out prediction
The system SHALL support bounded A100 prediction-only jobs that reuse the
existing private current-manifest tiny-overfit 7B adapter on the current public
manifest's `dev` and `test` splits without launching new training.

#### Scenario: Configure current tiny adapter dev/test prediction
- **WHEN** a developer prepares current tiny-adapter held-out prediction templates
- **THEN** the templates MUST use `dataset_manifest_id=public-sample-20260613T072200Z`
- **AND** they MUST use `prediction_split` values `dev` and `test`
- **AND** they MUST set `allow_private_prediction=true`, `overfit_diagnostic=false`, and `generalization_claim=false`
- **AND** they MUST keep private paths as `<a100_project_root>` placeholders and require a private override before remote execution
- **AND** they MUST NOT include `allow_heavy_training`, `adapter_output_dir`, or `max_prediction_rows`

#### Scenario: Launch prediction-only run with existing tiny adapter
- **WHEN** the current tiny-adapter held-out prediction job runs on A100 with an explicit private override, an approved private project root, and the existing private adapter path
- **THEN** the system MUST generate sanitized public-sample predictions and sidecars for the configured split without training, copying adapters, copying checkpoints, copying raw logs, or writing private runtime paths into public artifacts

#### Scenario: Reject accidental training or unresolved execution
- **WHEN** current tiny-adapter held-out prediction is attempted with unresolved placeholders, without explicit prediction opt-in, without an adapter path, with row-limited train-only config, or as a training command
- **THEN** the system MUST NOT load private model artifacts for prediction and MUST NOT start training
