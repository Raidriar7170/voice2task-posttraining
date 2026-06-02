## ADDED Requirements

### Requirement: Run A100 public-sample SFT smoke
The system SHALL provide a bounded, opt-in A100 SFT smoke workflow that trains the existing Qwen-family LoRA SFT path on the committed public sample and writes all remote outputs under the approved private A100 project root.

#### Scenario: Launch smoke with explicit opt-in
- **WHEN** a developer launches the A100 SFT smoke with `--run-training` and a config whose `allow_heavy_training` is `true`
- **THEN** the system uses the configured public-sample manifest, writes adapter/checkpoint outputs under the configured A100 project directory, and records the base model, dataset manifest ID, hyperparameters, package versions, output paths, and training command in adapter metadata

#### Scenario: Reject accidental heavy training
- **WHEN** a developer launches the A100 SFT smoke without `--run-training` or with `allow_heavy_training` unset or false
- **THEN** the system does not download models or start training and instead emits dry-run metadata that clearly states no heavy training occurred

#### Scenario: Keep remote evidence private by default
- **WHEN** the A100 smoke run completes
- **THEN** raw checkpoints, adapters, caches, and logs remain out of git unless a later explicit release change approves a sanitized artifact
