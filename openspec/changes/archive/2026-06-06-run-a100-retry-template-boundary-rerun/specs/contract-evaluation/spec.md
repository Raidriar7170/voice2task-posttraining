## ADDED Requirements

### Requirement: Publish A100 retry template boundary rerun evidence
The system SHALL publish public-safe train-split evidence for the A100 retry template boundary rerun that separates strict final metrics from retry-template observations and non-claims.

#### Scenario: Generate retry template rerun manifest
- **WHEN** rerun predictions, metrics, prompt snapshot, raw decoded summary, generation trace, retry-template boundary diagnosis, schema guard summary, and leak-scan results are available
- **THEN** the manifest MUST record `prediction_source_kind=private_a100_adapter`, `prediction_split=train`, `overfit_diagnostic=true`, `generalization_claim=false`, strict metric values, retry-template boundary metadata, raw/retry parse status counts, retry wrapper counts, schema-valid counts, source artifact links, and claim boundaries without private paths or host details

#### Scenario: Report retry template outcome
- **WHEN** a retry-template boundary diagnosis is generated
- **THEN** it MUST report per-row raw parse status, retry parse status, retry wrapper status, validated output source, strict schema validity, retry template boundary visibility, generation trace availability, and whether strict final metrics improved relative to the bounded prior A100 retry JSON-only rerun

#### Scenario: Preserve prior local and A100 evidence interpretation
- **WHEN** the evidence pack references prior artifacts
- **THEN** it MUST link `reports/public-sample/retry-template-decoding-boundary/` as local template-boundary evidence and `reports/public-sample/a100-retry-json-only-boundary-rerun/` as the prior A100 baseline, while stating that only the new rerun can support observed trained-adapter behavior claims for this template boundary

#### Scenario: Bound rerun interpretation
- **WHEN** public documentation or Human Briefs describe the rerun
- **THEN** they MUST state that the phase performs no training, checkpoint release, adapter release, parser relaxation, evaluator metric change, semantic-equivalence scoring, slot normalization, prediction repair, prediction re-score, held-out generalization claim, production-readiness claim, public full-corpus release, live-browser benchmark improvement claim, or model-quality claim
