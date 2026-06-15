## ADDED Requirements

### Requirement: Run slot value candidate SFT probe separately
The system SHALL support a bounded SFT probe over reviewed slot value generalization candidates without merging those candidates into the formal public sample.

#### Scenario: Select only candidate rows for SFT
- **WHEN** a developer runs the candidate SFT probe dry-run or training command
- **THEN** the run metadata MUST load the candidate-only manifest
- **AND** it MUST select exactly the materialized slot value candidate SFT rows
- **AND** it MUST NOT select formal public sample `dev` or `test` rows

#### Scenario: Keep candidate probe non-generalization
- **WHEN** candidate SFT probe metadata, reports, or Human Briefs are generated
- **THEN** they MUST label the run as candidate-only learning-signal or overfit-probe evidence
- **AND** they MUST set `generalization_claim=false`
- **AND** they MUST NOT claim held-out dev/test recovery, model recovery, adapter release, checkpoint release, production readiness, private-corpus generalization, or live-browser benchmark improvement

#### Scenario: Gate real A100 execution
- **WHEN** the candidate probe is prepared for A100 execution
- **THEN** committed configs MUST keep private paths unresolved with `<a100_project_root>` placeholders
- **AND** any real execution evidence MUST record whether train dependencies, private overrides, output-root policy, and idle GPU checks passed
- **AND** if dependencies or safe output placement are unavailable, the evidence MUST record a blocked status instead of implying training ran
