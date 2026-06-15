## ADDED Requirements

### Requirement: Run prediction-only hardened canonical policy rerun
The system SHALL support a bounded A100 prediction-only rerun that uses the
existing merged slot-value 7B adapter with the current hardened canonical prompt
policy.

#### Scenario: Configure split-specific prediction rerun
- **WHEN** hardened canonical policy rerun configs are committed
- **THEN** each config MUST target one of `train`, `dev`, or `test`
- **AND** each config MUST use the current public-sample manifest ID
- **AND** each config MUST point to the existing merged slot-value adapter via
  a private placeholder
- **AND** each config MUST NOT include training opt-ins such as
  `allow_heavy_training` or `adapter_output_dir`

#### Scenario: Preserve prediction-only boundary
- **WHEN** the rerun is launched on A100
- **THEN** it MUST run `sft-predict` and strict evaluation only
- **AND** it MUST NOT start SFT, DPO, GRPO, adapter continuation training, data
  regeneration, evaluator relaxation, prediction repair, or prediction
  replacement

#### Scenario: Prove hardened prompt policy visibility
- **WHEN** prediction metadata is imported for the rerun
- **THEN** it MUST record `clarify_ambiguity_canonical_phrase_visible=true`
  and `unsafe_payment_canonical_command_visible=true` for each split before
  the run is interpreted as hardened-policy evidence
