## ADDED Requirements

### Requirement: Publish form-fill confirmation and field-specificity policy
The system SHALL publish a public-safe form-fill confirmation and field-specificity policy artifact derived only from committed form-fill boundary inspection evidence before any future data, prompt, training, or evaluator remediation for the observed form-fill residual buckets.

#### Scenario: Define policy from form-fill inspection evidence
- **WHEN** the form-fill policy artifact is generated
- **THEN** the evidence MUST record the source manifest id, source inspection artifact, strict contract metrics, form-fill bucket counts, cluster-row incidence counts, residual-field counts, split counts, field paths, source-family counts, representative examples, and source count consistency
- **AND** it MUST include separate policy sections for confirmation markers, field specificity or alias drift, and route or intent boundary leakage
- **AND** it MUST preserve `cluster_row_incidence_total` terminology without presenting it as unique row count

#### Scenario: Preserve strict metric authority
- **WHEN** the form-fill policy artifact references strict and soft metrics
- **THEN** strict `contract_exact_match`, strict `slot_f1`, and the contract evaluation ladder MUST remain authoritative
- **AND** `slot_f1_soft` MUST remain an internal diagnostic only
- **AND** the artifact MUST NOT repair, normalize, replace, or re-score predictions

#### Scenario: Bound policy execution scope
- **WHEN** the form-fill policy artifact is generated
- **THEN** it MUST state that no prediction run, A100 job, SFT training, DPO training, GRPO training, dataset mutation, candidate generation, prompt change, gold policy mutation, evaluator relaxation, semantic-equivalence scoring, prediction repair, prediction replacement, or prediction re-score occurred
- **AND** it MUST NOT claim held-out recovery, model recovery, checkpoint release, adapter release, production readiness, private-corpus generalization, public full-corpus release, or live-browser benchmark improvement

#### Scenario: Recommend only bounded follow-up actions
- **WHEN** the form-fill policy artifact recommends follow-up work
- **THEN** recommendations MUST be labeled as candidate next actions derived from the observed policy sections
- **AND** recommendations MUST require separate OpenSpec phases before mutating data, prompts, gold policy, evaluator semantics, predictions, checkpoints, adapters, or training runs

#### Scenario: Validate policy artifact public safety
- **WHEN** form-fill policy artifacts are prepared for commit
- **THEN** leak-scan validation MUST reject raw private rows, absolute local paths, private remote paths, host details, SSH details, secrets, tokens, raw logs, checkpoints, adapters, caches, and oversized generated corpora
