## ADDED Requirements

### Requirement: Materialize form-fill confirmation-marker extension candidates separately
The system SHALL materialize reviewed form-fill confirmation-marker extension design cases into a public-safe candidate dataset that remains separate from the formal public sample until a later approved change explicitly merges it.

#### Scenario: Generate confirmation-marker extension candidate seeds
- **WHEN** the confirmation-marker extension materializer runs on a reviewed extension design artifact
- **THEN** it MUST write exactly one public-safe candidate seed row for each proposed candidate case
- **AND** each candidate seed MUST use a schema-valid Browser Task Contract with `task_type="form_fill"`, `route="fill_form"`, `confirmation_required=true`, and `safety.reason="requires_confirmation"`
- **AND** each candidate seed MUST include provenance linking back to the source design artifact, source case id, source family id, source bucket, field-label derivation status, and expected confirmation marker

#### Scenario: Preserve non-derivable field-label boundary
- **WHEN** a proposed candidate case has `field_label_derivation_status="not_derivable_from_committed_coverage_policy_artifacts"`
- **THEN** the materializer MUST NOT invent or expose private residual field labels
- **AND** the candidate provenance MUST label the field as a public-safe family-level candidate label rather than recovered gold text

#### Scenario: Expand candidate SFT rows without DPO
- **WHEN** confirmation-marker extension candidate seeds are generated
- **THEN** the materializer MUST expand them into candidate SFT rows using the existing SFT row schema and candidate provenance
- **AND** it MUST NOT generate DPO pairs or hard negatives in this phase

#### Scenario: Keep formal public sample unchanged
- **WHEN** confirmation-marker extension candidate materialization runs
- **THEN** it MUST NOT edit `data/public-samples/seed_traces.jsonl`, `sft_public_sample.jsonl`, `dpo_public_sample.jsonl`, or `manifest_public_sample.json`
- **AND** the materialization manifest MUST state `formal_public_sample_modified=false`, `seed_traces_modified=false`, `training_run=false`, `prediction_run=false`, `dpo_run=false`, `a100_execution=false`, and `evaluator_metric_change=false`

#### Scenario: Preserve evaluation and claim boundaries
- **WHEN** confirmation-marker extension candidate artifacts, reports, or Human Briefs describe the phase
- **THEN** they MUST state that strict `contract_exact_match`, strict `slot_f1`, and the contract evaluation ladder remain authoritative
- **AND** they MUST state that `slot_f1_soft` is diagnostic-only
- **AND** they MUST NOT claim held-out generalization recovery, model recovery, checkpoint release, adapter release, production readiness, private-corpus generalization, public full-corpus release, or live-browser benchmark improvement
