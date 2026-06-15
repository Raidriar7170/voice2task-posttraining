## ADDED Requirements

### Requirement: Design slot value generalization cases before materialization
The system SHALL publish a public-safe case-design artifact for targeted slot value generalization before modifying public sample seeds, generating rows, or launching training.

#### Scenario: Cover residual buckets
- **WHEN** targeted slot value residual diagnosis evidence is available
- **THEN** the case design MUST propose candidate case groups for `slot_value_language_variant`, `slot_value_canonical_phrase_drift`, and `normalized_command_paraphrase_drift`
- **AND** each candidate group MUST identify the residual source family, affected field path, canonical gold value, observed wrong value pattern, and intended training or validation purpose

#### Scenario: Keep design separate from data mutation
- **WHEN** the case design artifact is generated
- **THEN** it MUST state `new_data_generated=false`, `public_sample_modified=false`, and `training_run=false`
- **AND** it MUST require a later approved OpenSpec change before candidate cases are materialized into `seed_traces.jsonl`, rebuilt datasets, or training configs

#### Scenario: Preserve held-out and exact-match boundaries
- **WHEN** the case design recommends a next phase
- **THEN** it MUST preserve strict `contract_exact_match` as the primary metric
- **AND** it MUST NOT relax evaluator rules, normalize predictions, re-score prior evidence, promote semantic equivalence, or claim held-out recovery
