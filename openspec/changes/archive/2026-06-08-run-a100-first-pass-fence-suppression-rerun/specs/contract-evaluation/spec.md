## ADDED Requirements

### Requirement: Publish A100 first-pass fence-suppression rerun evidence
The system SHALL publish public-safe evidence for the A100 first-pass fence-suppression rerun with strict metric boundaries and explicit non-claims.

#### Scenario: Generate rerun evidence pack
- **WHEN** sanitized A100 prediction artifacts are available
- **THEN** the evidence pack MUST include predictions, prediction metadata, prompt snapshot, raw decoded summary, generation trace, metrics, schema guard summary, rerun diagnosis, manifest, human-readable report, leak scans, and a Human Brief

#### Scenario: Compare wrapper and strict metrics narrowly
- **WHEN** the rerun evidence is summarized
- **THEN** it MUST report prediction count, train row ids, Markdown-wrapped prediction count, raw and retry schema-valid counts, validated output schema-valid count, validated output source counts, strict JSON valid rate, strict exact match, stop-boundary trace fields, and comparison to prior first-pass output-boundary rerun evidence

#### Scenario: Bound rerun interpretation
- **WHEN** public reports or Human Briefs describe the rerun
- **THEN** they MUST state that this is train-internal prediction-only evidence and MUST NOT claim training, checkpoint release, adapter release, parser relaxation, evaluator metric change, prediction repair, prediction re-score, semantic-equivalence scoring, slot normalization, held-out generalization, production readiness, public full-corpus release, model-quality improvement, model recovery, or live-browser benchmark improvement
