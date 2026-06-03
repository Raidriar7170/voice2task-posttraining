## ADDED Requirements

### Requirement: Prepare runtime SFT label provenance checks
The system SHALL provide a public-safe preparation path for real tokenizer/collator SFT label provenance checks without launching private runtime execution by default.

#### Scenario: Prepare runtime check template
- **WHEN** a developer prepares the runtime label provenance check configuration
- **THEN** the committed template MUST keep private paths unresolved, require a repo-external private override, record approved output-root policy, and state that no A100/private adapter execution occurs from the public template

#### Scenario: Reject unresolved runtime execution
- **WHEN** runtime label provenance inspection is requested without a private override, with unresolved template paths, or without explicit runtime opt-in
- **THEN** the command MUST NOT download models, load private adapters, connect to A100 infrastructure, or inspect private labels, and MUST emit a structured blocked/skipped status

#### Scenario: Record runtime readiness metadata
- **WHEN** the runtime preparation command evaluates config and manifest inputs
- **THEN** the output MUST record runtime check status, private override requirement status, output-root policy status, dependency policy, label provenance intent, prior evidence links, and claim boundaries without exposing private paths or host details

### Requirement: Preserve runtime label evidence boundary
The system SHALL keep runtime readiness separate from true label-mask evidence until labels from the real tokenizer/collator training path are inspected.

#### Scenario: Report prepared but not inspected
- **WHEN** a runtime label provenance check is prepared but not executed
- **THEN** the result MUST keep true label-mask fields unavailable, set `label_tensor_available=false`, and state that runtime readiness does not prove Browser Task Contract learning

#### Scenario: Bound later runtime execution
- **WHEN** a later authorized runtime phase performs real tokenizer/collator label inspection
- **THEN** it MUST write only sanitized public-safe summaries to git and keep private overrides, raw logs, checkpoints, adapters, caches, host details, tokens, and private corpus rows outside committed artifacts
