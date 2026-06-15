## ADDED Requirements

### Requirement: Publish slot value candidate probe evidence safely
The system SHALL publish public-safe evidence for slot value candidate SFT probe preparation or execution without leaking private runtime artifacts or overstating model quality.

#### Scenario: Report candidate probe prep evidence
- **WHEN** local dry-run metadata and A100 preflight information are available
- **THEN** the report MUST record candidate row counts, selected row ids, training status, prediction status, dependency status, GPU preflight status, and artifact policy using public-safe values
- **AND** it MUST link the candidate manifest, candidate SFT rows, SFT config, prediction config, and prior materialization evidence

#### Scenario: Preserve public sample boundary
- **WHEN** candidate probe evidence is generated
- **THEN** it MUST state `formal_public_sample_modified=false`
- **AND** it MUST NOT rewrite or replace the formal public sample manifest, SFT JSONL, DPO JSONL, or seed traces

#### Scenario: Bound interpretation
- **WHEN** candidate probe evidence is described in reports or Human Briefs
- **THEN** it MUST state that candidate dry-run or blocked A100 status does not prove model recovery, held-out generalization, checkpoint release, adapter release, production readiness, private-corpus generalization, or live-browser improvement
