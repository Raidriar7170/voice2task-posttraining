# supervised-contract-tuning Specification

## Purpose
Define how supervised LoRA tuning teaches Qwen-family small instruction models to emit canonical browser task contracts from Chinese spoken commands or ASR transcripts.
## Requirements
### Requirement: Train supervised contract adapters
The system SHALL run LoRA SFT experiments that train a Qwen-family small instruction model to emit browser task contracts from Chinese spoken commands or ASR transcripts.

#### Scenario: Run SFT training
- **WHEN** a developer launches SFT training with a valid config and train/dev dataset paths
- **THEN** the system trains a LoRA adapter, writes checkpoints to a configured output directory, and records the model, dataset manifest, hyperparameters, and training command

### Requirement: Keep SFT outputs contract-focused
The system SHALL format supervised targets as browser task contracts rather than free-form assistant responses.

#### Scenario: Prepare SFT examples
- **WHEN** the training data formatter converts dataset rows into model messages
- **THEN** the target assistant content is the canonical browser task contract JSON and not explanatory prose

### Requirement: Provide prompt-only and rule baselines
The system SHALL support baseline evaluation for a rule normalizer and a prompt-only model before comparing SFT outputs.

#### Scenario: Compare SFT against baselines
- **WHEN** the SFT report is generated
- **THEN** it includes baseline metrics for at least rule normalization and prompt-only generation when the required providers or fixtures are available

### Requirement: Export adapter metadata
The system SHALL export SFT adapter metadata without implying a public checkpoint release unless an explicit release artifact exists.

#### Scenario: Export SFT adapter summary
- **WHEN** SFT training completes
- **THEN** the system writes an adapter summary containing base model, adapter path, dataset manifest ID, metrics path, and release status

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
