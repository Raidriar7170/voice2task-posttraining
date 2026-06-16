## ADDED Requirements

### Requirement: Publish form-fill boundary and field-specificity inspection
The system SHALL publish public-safe form-fill boundary and field-specificity inspection evidence derived only from committed formal held-out residual-cluster evidence before recommending data, prompt, training, or evaluator changes for the top form-fill residual clusters.

#### Scenario: Inspect form-fill residual buckets
- **WHEN** form-fill inspection is generated for the current formal public held-out residual clusters
- **THEN** the evidence MUST record the source manifest id, source residual-cluster report, strict contract metrics, form-fill cluster counts, bucket counts, split counts, source-family counts, and representative examples
- **AND** it MUST separate at least normalized-command residuals from slot residuals
- **AND** it MUST identify diagnostic buckets as candidates rather than root-cause proof

#### Scenario: Preserve analysis-only boundaries
- **WHEN** form-fill inspection evidence is generated
- **THEN** the evidence MUST state that no prediction run, A100 job, SFT training, DPO training, GRPO training, dataset mutation, prompt change, gold policy change, evaluator relaxation, semantic-equivalence scoring, prediction repair, prediction replacement, or prediction re-score occurred
- **AND** strict `contract_exact_match`, strict `slot_f1`, and the contract evaluation ladder MUST remain authoritative
- **AND** `slot_f1_soft` MUST remain an internal diagnostic only

#### Scenario: Bound follow-up recommendations
- **WHEN** the form-fill inspection recommends follow-up work
- **THEN** recommendations MUST be labeled as candidate next actions derived from observed form-fill residual buckets
- **AND** they MUST NOT mutate data, training, prompts, evaluator semantics, predictions, checkpoints, or adapter release status in the same phase
- **AND** they MUST NOT claim held-out recovery, model recovery, production readiness, private-corpus generalization, public full-corpus release, or live-browser benchmark improvement

#### Scenario: Validate form-fill inspection public safety
- **WHEN** form-fill inspection artifacts are prepared for commit
- **THEN** leak-scan validation MUST reject raw private rows, absolute local paths, private remote paths, host details, SSH details, secrets, tokens, raw logs, checkpoints, adapters, caches, and oversized generated corpora
