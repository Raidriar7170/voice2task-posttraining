## ADDED Requirements

### Requirement: Publish form-fill remediation case design
The system SHALL publish a public-safe, design-only `form_fill` remediation case-design artifact from the existing formal held-out remediation plan before any later materialization, training, DPO, A100, prediction rerun, or evaluator-policy change.

#### Scenario: Validate source plan boundary
- **WHEN** the form-fill remediation case design is generated
- **THEN** the source artifact MUST be `formal_heldout_form_fill_remediation_plan` evidence with `target="form_fill"` and `remediation_status="plan_only_no_data_no_training_no_metric_change"`

#### Scenario: Produce reviewed case groups
- **WHEN** the source plan contains remediation buckets
- **THEN** the case design MUST publish review-ready case groups and prompt/policy guidance for `confirmation_marker_missing_or_reordered`, `field_name_specificity_drift`, and `clarify_boundary_confusion`

#### Scenario: Preserve data and evaluation boundaries
- **WHEN** the case design report or manifest is generated
- **THEN** it MUST state that no seed rows, public-sample splits, held-out gold labels, SFT rows, DPO pairs, predictions, A100 jobs, training runs, or evaluator metrics were created or changed

#### Scenario: Keep claims bounded
- **WHEN** reports, manifests, Human Briefs, or OpenSpec artifacts describe the case-design phase
- **THEN** they MUST keep `contract_exact_match` and strict `slot_f1` as primary metrics, keep `slot_f1_soft` diagnostic-only, and MUST NOT claim model recovery, production readiness, checkpoint release, adapter release, full-corpus release, or live-browser benchmark improvement

#### Scenario: Validate public-safety of artifacts
- **WHEN** the case-design artifacts are prepared for commit
- **THEN** leak-scan validation MUST reject raw private rows, absolute local paths, private remote paths, host details, SSH details, secrets, tokens, raw logs, checkpoints, adapters, caches, and oversized generated corpora
