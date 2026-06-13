## ADDED Requirements

### Requirement: Diagnose current-manifest runtime label and tiny-overfit readiness
The system SHALL provide a bounded SFT debugging diagnostic that compares the current public manifest with available runtime-label and tiny-overfit artifacts before recommending any additional full SFT rerun.

#### Scenario: Treat stale runtime label evidence as prior context only
- **WHEN** a runtime-label artifact was generated for a dataset manifest ID that differs from the current public manifest ID
- **THEN** the diagnostic MUST mark the runtime evidence as stale for the current phase
- **AND** it MUST preserve the stale artifact's label-mask fields only as prior context
- **AND** it MUST NOT claim that current public rows have inspected runtime labels

#### Scenario: Preserve fresh runtime label mask fields
- **WHEN** a runtime-label artifact matches the current public manifest ID and reports real training labels
- **THEN** the diagnostic MUST record `true_label_mask_status`, `prompt_tokens_masked`, `assistant_tokens_carry_loss`, prompt token count, assistant token count, label source kind, and evidence gaps
- **AND** it MUST distinguish assistant-token loss participation from an assistant-only loss-mask claim

#### Scenario: Bound tiny-overfit recommendation
- **WHEN** current runtime labels are unavailable or stale after local public-safe inspection
- **THEN** the diagnostic MUST recommend a fresh current-manifest runtime label check before a full SFT rerun
- **AND** it MAY recommend a 1-3 row tiny-overfit probe only as train-internal objective debugging
- **AND** it MUST NOT present tiny-overfit as held-out generalization, model recovery, checkpoint release, adapter release, production readiness, or live-browser benchmark evidence

#### Scenario: Avoid widening into full training
- **WHEN** the bounded diagnostic is run locally
- **THEN** it MUST NOT run full SFT, DPO, GRPO, private adapter prediction, or model release steps
- **AND** it MUST NOT copy checkpoints, adapters, caches, raw logs, private paths, host details, SSH details, or private corpus rows into committed artifacts
