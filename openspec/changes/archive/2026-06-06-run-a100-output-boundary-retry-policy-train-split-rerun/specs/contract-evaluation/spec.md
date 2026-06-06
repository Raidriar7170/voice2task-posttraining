## ADDED Requirements

### Requirement: Publish output-boundary retry-policy A100 rerun evidence
The system SHALL publish public-safe train-split evidence for the output-boundary retry-policy A100 rerun that separates strict final metrics from row-level schema boundary, retry wrapper, task type, route, safety, confirmation, slot, and normalized-command observations while preserving non-claim boundaries.

#### Scenario: Generate output-boundary retry-policy rerun manifest
- **WHEN** train-split rerun predictions, metrics, prompt snapshot, raw decoded summary, generation trace, row-level diagnosis, schema guard summary, and leak-scan results are available
- **THEN** the manifest MUST record `prediction_source_kind=private_a100_adapter`, `prediction_split=train`, `overfit_diagnostic=true`, `generalization_claim=false`, strict metric values, row-level field counts, retry and parser status counts, prompt/retry policy visibility, and claim boundaries without private paths or host details

#### Scenario: Report output-boundary retry diagnosis
- **WHEN** an output-boundary retry-policy diagnosis is generated for the rerun
- **THEN** it MUST report per-row gold/predicted field summaries, raw and retry parse status, exact field match status for `task_type`, `route`, `safety.reason`, `confirmation_required`, `slots`, and `normalized_command`, aggregate field counts, family counts, and whether the row was otherwise schema-valid without normalizing or re-scoring predictions

#### Scenario: Compare against prior A100 and local repair evidence narrowly
- **WHEN** the public report describes the rerun result
- **THEN** it MUST compare only against `reports/public-sample/a100-public-readonly-search-policy-train-split-rerun/` and `reports/public-sample/public-readonly-output-boundary-retry-policy/` and MUST NOT present the comparison as dev/test generalization or model-quality improvement

#### Scenario: Validate output-boundary retry rerun evidence boundaries
- **WHEN** the evidence pack is prepared for commit
- **THEN** leak-scan validation MUST reject raw private rows, local or remote private paths, secrets, private IP addresses, SSH details, raw logs, checkpoints, adapters, caches, oversized generated corpora, and private remote paths

#### Scenario: Bound output-boundary retry rerun interpretation
- **WHEN** public documentation or Human Briefs describe the output-boundary retry-policy rerun
- **THEN** they MUST state that the phase performs no training, checkpoint release, adapter release, evaluator metric change, semantic-equivalence scoring, slot normalization, prediction repair, prediction re-score, production-readiness claim, held-out generalization claim, public full-corpus release, model-quality claim, or live-browser benchmark improvement claim
