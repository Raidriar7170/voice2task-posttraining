## ADDED Requirements

### Requirement: Publish A100 retry JSON-only boundary rerun evidence
The system SHALL publish public-safe train-split evidence for the A100 retry JSON-only boundary rerun that separates strict final metrics from retry-boundary observations and non-claims.

#### Scenario: Generate retry-boundary rerun manifest
- **WHEN** rerun predictions, metrics, prompt snapshot, raw decoded summary, generation trace, retry-boundary diagnosis, schema guard summary, and leak-scan results are available
- **THEN** the manifest MUST record `prediction_source_kind=private_a100_adapter`, `prediction_split=train`, `overfit_diagnostic=true`, `generalization_claim=false`, strict metric values, retry prompt constraint visibility, raw/retry parse status counts, retry wrapper counts, schema-valid counts, source artifact links, and claim boundaries without private paths or host details

#### Scenario: Report retry-boundary outcome
- **WHEN** a retry-boundary diagnosis is generated
- **THEN** it MUST report per-row raw parse status, retry parse status, retry wrapper status, validated output source, strict schema validity, retry trace availability, and whether strict final metrics improved relative to the bounded prior A100 stop-boundary rerun

#### Scenario: Bound rerun interpretation
- **WHEN** public documentation or Human Briefs describe the rerun
- **THEN** they MUST state that the phase performs no training, checkpoint release, adapter release, parser relaxation, evaluator metric change, semantic-equivalence scoring, slot normalization, prediction repair, prediction re-score, held-out generalization claim, production-readiness claim, model-quality claim, public full-corpus release, or live-browser benchmark improvement claim
