## ADDED Requirements

### Requirement: Retry form-fill remediation SFT v3 after SSH recovery
The system SHALL retry the blocked `form_fill` remediation SFT v3 run only
after fresh A100 connectivity and GPU preflight succeed.

#### Scenario: Repeat preflight before retry training
- **WHEN** the retry phase starts after an SSH timeout blocker
- **THEN** it MUST run fresh A100 connectivity and GPU occupancy checks
- **AND** it MUST select a safe GPU explicitly with `CUDA_VISIBLE_DEVICES`
  before training
- **AND** it MUST NOT reuse the previous blocked status as evidence that GPU
  placement is safe

#### Scenario: Keep retry training private
- **WHEN** retry training starts
- **THEN** private overrides, checkpoints, adapters, raw logs, model caches,
  host details, SSH details, tokens, and private paths MUST remain outside git
- **AND** committed evidence MUST use sanitized summaries and public-safe
  placeholders

#### Scenario: Stop safely on retry blockers
- **WHEN** SSH, GPU placement, dependency setup, training, or output-root policy
  cannot be verified safely
- **THEN** the retry phase MUST record blocked or failed evidence without
  launching unsafe work or fabricating adapter metadata
