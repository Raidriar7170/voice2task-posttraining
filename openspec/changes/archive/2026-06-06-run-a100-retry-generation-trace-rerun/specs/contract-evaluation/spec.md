## ADDED Requirements

### Requirement: Publish A100 retry generation trace rerun evidence
The system SHALL publish public-safe train-split evidence for the retry generation trace A100 rerun that separates strict final metrics from raw/retry attempt generation-trace observations while preserving non-claim boundaries.

#### Scenario: Generate retry trace rerun manifest
- **WHEN** train-split rerun predictions, metrics, prompt snapshot, raw decoded summary, generation trace, retry-trace diagnosis, schema guard summary, and leak-scan results are available
- **THEN** the manifest MUST record `prediction_source_kind=private_a100_adapter`, `prediction_split=train`, `overfit_diagnostic=true`, `generalization_claim=false`, strict metric values, raw/retry trace attempt counts, retry wrapper counts, prompt/retry policy visibility, and claim boundaries without private paths or host details

#### Scenario: Report retry trace diagnosis
- **WHEN** a retry trace diagnosis is generated
- **THEN** it MUST report per-row raw/retry trace availability, generated token count, max token limit, EOS visibility, finish state, retry parse status, retry wrapper status, strict final schema validity, and whether any retry stop-boundary claim remains unproven

#### Scenario: Compare only against bounded prior evidence
- **WHEN** the public report describes the rerun result
- **THEN** it MUST compare only against `reports/public-sample/a100-schema-retry-wrapper-boundary-rerun/` and `reports/public-sample/retry-generation-trace-instrumentation/` and MUST NOT present the comparison as held-out generalization or model-quality improvement

#### Scenario: Bound retry trace rerun interpretation
- **WHEN** public documentation or Human Briefs describe the rerun
- **THEN** they MUST state that the phase performs no training, checkpoint release, adapter release, decoding behavior change, retry prompt change, parser relaxation, evaluator metric change, semantic-equivalence scoring, slot normalization, prediction repair, prediction re-score, production-readiness claim, held-out generalization claim, model-quality claim, public full-corpus release, or live-browser benchmark improvement claim
