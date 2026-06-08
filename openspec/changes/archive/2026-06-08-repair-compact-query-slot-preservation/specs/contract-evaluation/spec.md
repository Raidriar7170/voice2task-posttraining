## ADDED Requirements

### Requirement: Publish compact query slot preservation repair evidence
The system SHALL publish public-safe local evidence for compact query slot preservation reinforcement without reinterpreting historical A100 predictions.

#### Scenario: Generate compact query preservation evidence pack
- **WHEN** the local compact-query preservation repair phase completes
- **THEN** the evidence pack MUST include prompt constraint metadata, public sample SFT target checks, public DPO decomposed-slot rejected pair checks, source residual diagnosis links, validation commands, leak-scan results, and explicit non-claims
- **AND** it MUST record that no A100 execution, training, prediction rerun, evaluator change, parser change, semantic-equivalence scoring, slot normalization, prediction repair, prediction replacement, or re-score was performed

#### Scenario: Bound compact query preservation interpretation
- **WHEN** evidence, Human Briefs, loop reports, or archived OpenSpec artifacts describe the repair
- **THEN** they MUST state that prior A100 predictions remain historical evidence and are not repaired, normalized, re-scored, or reinterpreted as exact-match recovery
- **AND** they MUST NOT claim held-out generalization, production readiness, model-quality improvement, model recovery, checkpoint release, adapter release, public full-corpus release, or live-browser benchmark improvement
