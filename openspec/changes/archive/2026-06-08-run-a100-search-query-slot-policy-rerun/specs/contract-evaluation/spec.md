## ADDED Requirements

### Requirement: Publish compact search query rerun evidence without metric reinterpretation
The system SHALL publish a public-safe evidence pack for the A100 search query slot-policy rerun that reports strict metrics and row-level slot/exact-match outcomes without reinterpreting prior predictions.

#### Scenario: Generate rerun evidence pack
- **WHEN** the A100 prediction-only rerun completes
- **THEN** the evidence pack MUST include predictions, gold train rows, prediction metadata, prompt snapshot, raw decoded summary, generation trace, metrics, schema guard summary, slot-policy rerun diagnosis, manifest, report, leak scans, and Human Brief links
- **AND** it MUST compare against the prior retry-template A100 rerun, the prior slot mismatch diagnosis, and the local search query slot target policy evidence
- **AND** it MUST record compact `slots.query` target checks, `city/date` slot counts, exact-match counts, slot mismatch counts, and normalized-command mismatch counts for the three train rows

#### Scenario: Bound claims
- **WHEN** reports, manifests, Human Briefs, or archived OpenSpec artifacts describe the rerun
- **THEN** they MUST state that this is train-split-only prediction evidence
- **AND** they MUST NOT claim held-out generalization, model-quality improvement, production readiness, checkpoint release, adapter release, public full-corpus release, live-browser benchmark improvement, slot normalization, semantic-equivalence scoring, prediction repair, prediction replacement, metric relaxation, or re-score
