## ADDED Requirements

### Requirement: Run compact search query policy prediction-only A100 rerun
The system SHALL support a bounded A100 prediction-only train-split rerun that exercises the current compact public-readonly search query slot target policy against an existing private adapter without training or releasing model artifacts.

#### Scenario: Execute train-split prediction-only rerun
- **WHEN** the rerun is launched on the A100 machine
- **THEN** it MUST use `prediction_split=train`, `overfit_diagnostic=true`, `generalization_claim=false`, `schema_retry_enabled=true`, greedy decoding, and the current public sample manifest
- **AND** it MUST use a repo-external private override with adapter/model/cache/output paths under the approved A100 project root
- **AND** it MUST inspect GPU occupancy, select a safe GPU, and set `CUDA_VISIBLE_DEVICES` explicitly
- **AND** it MUST NOT perform training, fine-tuning, DPO, GRPO, checkpoint release, adapter release, parser relaxation, evaluator metric change, slot normalization, semantic-equivalence scoring, prediction repair, prediction replacement, or re-score

#### Scenario: Preserve private runtime boundaries
- **WHEN** artifacts are copied back into the repository
- **THEN** only sanitized public sample evidence MAY be committed
- **AND** private overrides, raw logs, private paths, host details, SSH details, tokens, secrets, caches, checkpoints, adapters, and private corpus rows MUST remain outside git
