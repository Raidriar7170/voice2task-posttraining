## ADDED Requirements

### Requirement: Publish post-form-fill-remediation held-out evidence
The system SHALL publish public-safe prediction-only held-out evidence after the formal public sample includes reviewed `form_fill` remediation candidates.

#### Scenario: Evaluate against the current merged manifest
- **WHEN** sanitized private-adapter predictions are generated for the current formal public sample dev and test splits after the form-fill remediation merge
- **THEN** the system MUST evaluate them with the existing strict contract ladder
- **AND** the evidence MUST record the current public manifest id, formal counts, split counts, prediction split, and prediction artifact set

#### Scenario: Preserve prediction-only and strict-metric boundaries
- **WHEN** post-form-fill-remediation held-out evidence is generated
- **THEN** the evidence MUST state that no SFT training, DPO training, GRPO training, dataset mutation, evaluator relaxation, semantic-equivalence scoring, slot normalization, prediction repair, prediction replacement, or prediction re-score occurred
- **AND** strict `contract_exact_match`, strict `slot_f1`, and the contract evaluation ladder MUST remain authoritative
- **AND** `slot_f1_soft` MUST remain an internal diagnostic only

#### Scenario: Bound evidence interpretation
- **WHEN** reports or Human Briefs describe the post-form-fill-remediation held-out result
- **THEN** they MUST NOT claim held-out recovery, model recovery, checkpoint release, adapter release, production readiness, public full-corpus release, private-corpus generalization, or live-browser benchmark improvement unless a later scoped phase adds separate evidence for that claim

#### Scenario: Record blocked execution safely
- **WHEN** prediction-only execution cannot safely run because the adapter, private override, remote dependency, or idle GPU state is unavailable
- **THEN** the system MUST record a blocked status without writing fabricated predictions or model-quality metrics

#### Scenario: Validate public evidence boundaries
- **WHEN** post-form-fill-remediation held-out artifacts are prepared for commit
- **THEN** leak-scan validation MUST reject raw private rows, absolute local paths, private remote paths, host details, SSH details, secrets, tokens, raw logs, checkpoints, adapters, caches, and oversized generated corpora
