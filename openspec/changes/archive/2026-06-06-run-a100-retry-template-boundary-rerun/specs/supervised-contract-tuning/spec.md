## ADDED Requirements

### Requirement: Run A100 retry template boundary rerun
The system SHALL support a bounded A100 prediction-only train-split rerun after local retry template boundary hardening while keeping private runtime artifacts outside git.

#### Scenario: Launch retry template boundary rerun
- **WHEN** a developer launches the rerun with A100 authorization, a repo-external private override, an existing private adapter path, an idle A100 GPU, and an approved private output root represented in public artifacts as `<a100_project_root>`
- **THEN** the system MUST use `prediction_split=train`, `overfit_diagnostic=true`, `generalization_claim=false`, `schema_retry_enabled=true`, `schema_repair_applied=false`, the machine-only retry template boundary, strict parser semantics, and generate private-adapter predictions plus public-safe prompt snapshot, raw decoded summary, generation trace, prediction metadata, and leak-scan sidecars

#### Scenario: Preserve strict retry semantics
- **WHEN** the private adapter emits retry output that is Markdown-wrapped, prose-wrapped, fragmentary, schema-invalid, or otherwise invalid
- **THEN** the prediction artifact and sidecars MUST preserve sanitized model evidence without extracting embedded contracts, repairing predictions, relaxing parser semantics, normalizing fields, re-scoring outputs, or replacing outputs with fixture or gold contracts

#### Scenario: Keep private A100 artifacts private
- **WHEN** the real rerun completes, fails, or is blocked by GPU/runtime safety
- **THEN** raw logs, checkpoints, adapters, caches, private overrides, host details, SSH details, private paths, tokens, and private corpus rows MUST remain outside committed artifacts

#### Scenario: Enforce A100 placement safety
- **WHEN** the rerun is launched on A100 hardware
- **THEN** GPU and process occupancy MUST be inspected first, an idle GPU MUST be selected when available, `CUDA_VISIBLE_DEVICES` MUST be set explicitly, and other users' processes MUST NOT be killed, signaled, paused, reniced, or otherwise interrupted
