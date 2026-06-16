## ADDED Requirements

### Requirement: Check form-fill confirmation-marker extension candidate integration preview
The system SHALL support a local preview integration check for standalone form-fill confirmation-marker extension candidate seeds before any later formal public sample merge, training, or held-out evaluation decision.

#### Scenario: Build preview dataset from extension candidates
- **WHEN** the preview integration check runs with the current formal public seed file and the standalone confirmation-marker extension candidate seed file
- **THEN** it MUST validate exactly the reviewed extension candidate seed rows
- **AND** it MUST build a report-scoped preview public dataset that combines formal seed rows plus the extension candidate seed rows
- **AND** it MUST record formal counts before preview, preview counts, preview split counts, candidate contribution counts, and candidate source identity

#### Scenario: Keep formal public sample unchanged
- **WHEN** the preview integration check runs
- **THEN** it MUST NOT edit `data/public-samples/seed_traces.jsonl`, `sft_public_sample.jsonl`, `dpo_public_sample.jsonl`, or `manifest_public_sample.json`
- **AND** the evidence manifest MUST state `formal_public_sample_modified=false`, `preview_only_not_formal_public_sample=true`, `training_run=false`, `prediction_run=false`, `a100_execution=false`, and `evaluator_metric_change=false`

#### Scenario: Validate preview artifacts
- **WHEN** the preview dataset is built
- **THEN** the check MUST validate the preview SFT, DPO, and manifest artifacts through the public dataset validator
- **AND** preview DPO pairs MUST be labeled as preview-only validation artifacts rather than committed formal DPO changes

#### Scenario: Preserve claim boundaries
- **WHEN** preview integration evidence, reports, or Human Briefs describe the phase
- **THEN** they MUST state that strict `contract_exact_match`, strict `slot_f1`, and the contract evaluation ladder remain authoritative
- **AND** they MUST state that `slot_f1_soft` is diagnostic-only
- **AND** they MUST NOT claim held-out generalization recovery, model recovery, checkpoint release, adapter release, production readiness, private-corpus generalization, public full-corpus release, or live-browser benchmark improvement
