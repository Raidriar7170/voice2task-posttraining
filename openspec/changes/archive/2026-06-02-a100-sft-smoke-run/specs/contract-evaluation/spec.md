## ADDED Requirements

### Requirement: Publish sanitized A100 smoke evidence
The system SHALL produce a public-safe A100 SFT smoke evidence summary that reports training metadata, contract metrics, controlled smoke status, and leak-scan results without exposing private infrastructure or unreleased model artifacts.

#### Scenario: Generate smoke evidence report
- **WHEN** sanitized adapter metadata and public-sample predictions are available from the A100 SFT smoke
- **THEN** the system writes a machine-readable run manifest and a human-readable report that link the base model, manifest ID, metrics path, controlled smoke result, and release status without claiming a public checkpoint

#### Scenario: Validate evidence boundaries
- **WHEN** the evidence pack is prepared for commit
- **THEN** leak-scan validation rejects raw private rows, local absolute paths, secrets, tokens, private IP addresses, SSH details, and oversized generated corpora

#### Scenario: Separate smoke evidence from benchmark claims
- **WHEN** the public report describes A100 smoke results
- **THEN** it labels the result as a public-sample training smoke and contract-level evaluation, not as a live-browser benchmark improvement or production-readiness claim
