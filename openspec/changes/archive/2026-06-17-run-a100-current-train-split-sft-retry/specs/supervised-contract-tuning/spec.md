## ADDED Requirements

### Requirement: Run current-train-split SFT retry after readiness evidence
The system SHALL run at most one bounded private A100 SFT retry on the current
formal public train split after current-train-split retry readiness evidence is
complete.

#### Scenario: Repeat A100 preflight before current retry training
- **WHEN** the current-train-split SFT retry phase starts
- **THEN** it MUST run fresh A100 connectivity, GPU occupancy, disk/cache/temp,
  approved-root, dependency, manifest-count, and readiness-evidence checks
- **AND** it MUST select a safe GPU explicitly with `CUDA_VISIBLE_DEVICES`
  before training
- **AND** it MUST stop with blocked evidence if safe placement cannot be
  determined without interrupting other users

#### Scenario: Train only from the current formal public train split
- **WHEN** retry training starts
- **THEN** it MUST use manifest `public-sample-20260616T165835Z` and the train
  split of 118 SFT rows
- **AND** it MUST use a runtime/output label distinct from prior SFT v3 runs,
  `a100-current-train-split-sft-retry`
- **AND** it MUST NOT mutate public sample rows, prompts, evaluator metrics, or
  prediction artifacts before training

#### Scenario: Keep current retry artifacts private
- **WHEN** retry training or prediction runs
- **THEN** private overrides, checkpoints, adapters, raw logs, model caches,
  host details, SSH details, tokens, and private paths MUST remain outside git
- **AND** committed evidence MUST use sanitized summaries and public-safe
  placeholders
