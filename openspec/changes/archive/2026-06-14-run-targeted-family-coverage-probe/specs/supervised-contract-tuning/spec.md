## ADDED Requirements

### Requirement: Run targeted family coverage SFT probe
The system SHALL support a bounded A100 SFT probe that trains on explicit public-safe source families matching the current held-out residual train analogs.

#### Scenario: Select train rows by source family
- **WHEN** SFT training is launched with `train_source_ids`
- **THEN** the training path MUST filter the configured training split to rows whose provenance `source_id` is in that list
- **AND** training metadata MUST record selected source IDs, selected row IDs, rows before filtering, and rows after filtering

#### Scenario: Configure targeted family coverage training
- **WHEN** the targeted family coverage probe config is prepared
- **THEN** it MUST use base model `Qwen/Qwen2.5-7B-Instruct`, dataset manifest `public-sample-20260613T072200Z`, `dataset_split=train`, `allow_heavy_training=true`, and explicit train source IDs for `seed-open-help`, `seed-clarify-target`, `seed-form-nickname`, and `seed-block-transfer`
- **AND** it MUST keep `<a100_project_root>` placeholders and require a private override before remote execution

#### Scenario: Predict targeted family coverage splits
- **WHEN** targeted family coverage prediction configs are prepared
- **THEN** the system MUST provide split-specific train, dev, and test templates that point to the targeted probe adapter placeholder and require explicit prediction opt-in
- **AND** train prediction MUST be interpreted as learnability evidence while dev/test remain the primary held-out evidence

#### Scenario: Keep targeted probe private by default
- **WHEN** the targeted family coverage training or prediction run completes
- **THEN** raw logs, checkpoints, adapters, caches, private overrides, host details, SSH details, tokens, private paths, and private corpus rows MUST remain outside committed artifacts
