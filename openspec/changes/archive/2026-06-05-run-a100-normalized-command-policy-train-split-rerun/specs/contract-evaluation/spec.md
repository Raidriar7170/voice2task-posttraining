## ADDED Requirements

### Requirement: Publish normalized-command policy A100 rerun evidence
The system SHALL publish public-safe train-split evidence for the normalized-command policy A100 rerun that separates strict final metrics from normalized-command exact-string observations and preserves non-claim boundaries.

#### Scenario: Generate normalized-command rerun manifest
- **WHEN** train-split rerun predictions, metrics, prompt snapshot, raw decoded summary, generation trace, normalized-command diagnosis, and leak-scan results are available
- **THEN** the manifest MUST record `prediction_source_kind=private_a100_adapter`, `prediction_split=train`, `overfit_diagnostic=true`, `generalization_claim=false`, strict metric values, normalized-command exact-match counts, and claim boundaries without private paths or host details

#### Scenario: Report normalized-command exact-string diagnosis
- **WHEN** a normalized-command diagnosis is generated for the rerun
- **THEN** it MUST report per-row gold/predicted normalized-command summaries, exact-string match status, mismatch categories, aggregate exact-match counts, and whether the row was otherwise schema-valid without normalizing or re-scoring predictions

#### Scenario: Compare against prior A100 baseline narrowly
- **WHEN** the public report describes the rerun result
- **THEN** it MUST compare only against `reports/public-sample/a100-confirmation-required-train-split-rerun/` for train-split prediction-only evidence and MUST NOT present the comparison as dev/test generalization or model-quality improvement

#### Scenario: Validate normalized-command rerun evidence boundaries
- **WHEN** the evidence pack is prepared for commit
- **THEN** leak-scan validation MUST reject raw private rows, local or remote private paths, secrets, private IP addresses, SSH details, raw logs, checkpoints, adapters, caches, oversized generated corpora, and private remote paths

#### Scenario: Bound normalized-command rerun interpretation
- **WHEN** public documentation or Human Briefs describe the normalized-command rerun
- **THEN** they MUST state that the phase performs no training, checkpoint release, adapter release, evaluator metric change, semantic-equivalence scoring, prediction repair, prediction re-score, production-readiness claim, held-out generalization claim, public full-corpus release, model-quality claim, or live-browser benchmark improvement claim
