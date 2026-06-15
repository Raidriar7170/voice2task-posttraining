## ADDED Requirements

### Requirement: Publish merged slot value residual diagnosis evidence
The system SHALL publish public-safe residual diagnosis evidence for the merged slot-value held-out evaluation without changing strict evaluator semantics or model outputs.

#### Scenario: Diagnose residuals from available prediction artifacts
- **WHEN** gold public-sample rows and merged slot-value dev/test prediction artifacts are available
- **THEN** the diagnosis output MUST list each strict residual row by split, row id, task family, mismatch field paths, mismatch categories, and sanitized gold/prediction value summaries
- **AND** it MUST include aggregate residual counts by split, task family, field path, and category

#### Scenario: Separate strict metrics from soft diagnostics
- **WHEN** residual diagnosis references `contract_exact_match`, strict `slot_f1`, and `slot_f1_soft`
- **THEN** the report MUST keep strict `contract_exact_match` and strict `slot_f1` as authoritative metrics
- **AND** it MUST label `slot_f1_soft` as an internal diagnostic that does not repair, normalize, re-score, or replace strict predictions

#### Scenario: Preserve public-safe evidence boundaries
- **WHEN** residual diagnosis evidence is prepared for commit
- **THEN** leak-scan validation MUST reject raw private rows, absolute local paths, private remote paths, host details, SSH details, secrets, tokens, raw logs, checkpoints, adapters, caches, and oversized generated corpora

#### Scenario: Bound residual interpretation
- **WHEN** public reports or Human Briefs describe the residual diagnosis
- **THEN** they MUST state that this phase performs no training, prediction rerun, evaluator relaxation, semantic-equivalence scoring, slot normalization, prediction repair, prediction replacement, or prediction re-score
- **AND** they MUST NOT claim held-out recovery, model recovery, checkpoint release, adapter release, production readiness, public full-corpus release, private-corpus generalization, or live-browser benchmark improvement

#### Scenario: Recommend next bounded decision only
- **WHEN** diagnosis identifies the likely source of the remaining strict residuals
- **THEN** the report MAY recommend a next bounded OpenSpec phase
- **AND** it MUST NOT automatically materialize new data, change gold policy, launch training, or change evaluator behavior as part of the diagnosis phase
