## ADDED Requirements

### Requirement: Run A100 public held-out prediction with existing adapter
The system SHALL support bounded A100 public held-out prediction jobs that reuse an existing private 7B SFT adapter without launching new training.

#### Scenario: Configure public dev/test prediction
- **WHEN** a developer prepares public held-out prediction templates
- **THEN** the templates MUST use the committed public-sample manifest, set `prediction_split` to `dev` or `test`, keep private paths as `<a100_project_root>` placeholders, require `allow_private_prediction=true`, and set `generalization_claim=false`

#### Scenario: Launch prediction-only held-out run
- **WHEN** the held-out prediction job runs on A100 with an explicit private override, an approved private project root, and an existing private adapter path
- **THEN** the system MUST generate sanitized public-sample predictions and sidecars for the configured split without training, copying adapters, copying checkpoints, copying raw logs, or writing private runtime paths into public artifacts

#### Scenario: Reject accidental training or unresolved execution
- **WHEN** held-out prediction is attempted with unresolved placeholders, without explicit prediction opt-in, without an adapter path, or as a training command
- **THEN** the system MUST NOT load private model artifacts for prediction and MUST NOT start training
