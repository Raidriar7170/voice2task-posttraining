## ADDED Requirements

### Requirement: Publish current-train-split SFT retry readiness evidence
The system SHALL publish public-safe readiness-only evidence before launching a new bounded A100 SFT retry after train-only repair rows have been materialized into the current formal public sample.

#### Scenario: Verify current train split retry inputs
- **WHEN** a current-train-split SFT retry readiness report is generated
- **THEN** it MUST record manifest id `public-sample-20260616T165835Z`, 100 seed rows, 256 SFT rows, 864 DPO pairs, split counts of train 118 / dev 69 / test 69, and local dry-run selection of all 118 train rows
- **AND** it MUST record train-split coverage for the merged form-fill remediation / confirmation-marker rows and blocked-payment repair rows

#### Scenario: Preserve readiness-only boundary
- **WHEN** current-train-split SFT retry readiness evidence is prepared for commit
- **THEN** committed artifacts MUST state that no A100 SFT training, DPO training, GRPO training, prediction generation, dataset mutation, prompt change, evaluator relaxation, semantic-equivalence scoring, slot normalization, prediction repair, or prediction replacement was performed
- **AND** committed artifacts MUST NOT claim held-out recovery, model recovery, checkpoint release, adapter release, production readiness, public full-corpus release, private-corpus generalization, safety improvement, or live-browser benchmark improvement

#### Scenario: Require distinct future retry runtime
- **WHEN** public-safe configs are prepared for a future current-train-split SFT retry
- **THEN** they MUST use placeholder private roots, require private overrides, keep outputs private by default, and use a source/runtime label distinct from the previous `a100-form-fill-remediation-sft-v3` adapter
- **AND** they MUST NOT contain raw private paths, host details, SSH details, tokens, checkpoints, adapters, caches, or private corpus rows

#### Scenario: Bind readiness recommendation to current strict metrics
- **WHEN** the readiness report recommends a later bounded A100 SFT retry
- **THEN** it MUST cite the latest current-manifest prediction-only strict metrics as input evidence
- **AND** it MUST keep `contract_exact_match` and strict `slot_f1` as headline metrics while treating `slot_f1_soft` as diagnostic-only
