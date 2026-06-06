## ADDED Requirements

### Requirement: Publish schema retry wrapper-boundary A100 rerun evidence
The system SHALL publish public-safe train-split evidence for the schema retry wrapper-boundary A100 rerun that separates strict final metrics from row-level retry wrapper, task type, route, safety, confirmation, slot, and normalized-command observations while preserving non-claim boundaries.

#### Scenario: Generate retry wrapper-boundary rerun manifest
- **WHEN** train-split rerun predictions, metrics, prompt snapshot, raw decoded summary, generation trace, row-level diagnosis, schema guard summary, and leak-scan results are available
- **THEN** the manifest MUST record `prediction_source_kind=private_a100_adapter`, `prediction_split=train`, `overfit_diagnostic=true`, `generalization_claim=false`, strict metric values, row-level counts, retry wrapper counts, prompt/retry policy visibility, and claim boundaries without private paths or host details

#### Scenario: Compare only against bounded prior evidence
- **WHEN** the public report describes the rerun result
- **THEN** it MUST compare only against `reports/public-sample/a100-output-boundary-retry-policy-train-split-rerun/` and `reports/public-sample/schema-retry-wrapper-boundary-policy/` and MUST NOT present the comparison as held-out generalization or model-quality improvement

#### Scenario: Bound retry wrapper-boundary rerun interpretation
- **WHEN** public documentation or Human Briefs describe the rerun
- **THEN** they MUST state that the phase performs no training, checkpoint release, adapter release, parser relaxation, evaluator metric change, semantic-equivalence scoring, slot normalization, prediction repair, prediction re-score, production-readiness claim, held-out generalization claim, model-quality claim, or live-browser benchmark improvement claim
