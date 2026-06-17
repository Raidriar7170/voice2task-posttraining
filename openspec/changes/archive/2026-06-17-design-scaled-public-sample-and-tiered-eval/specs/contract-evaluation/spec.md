## ADDED Requirements

### Requirement: Design diagnostic tiered evaluation without relaxing strict metrics
The system SHALL publish a diagnostic tiered-evaluation design that decomposes strict contract failures while preserving strict public headline metrics.

#### Scenario: Define tiered diagnostic ladder
- **WHEN** a tiered-evaluation design phase runs
- **THEN** it MUST define diagnostic tiers for schema/structure validity, task type and route, safety and confirmation, slot exactness, and full-contract exactness
- **AND** it MUST identify which existing metrics or failure slices support each tier

#### Scenario: Preserve strict metric authority
- **WHEN** tiered-evaluation artifacts describe model quality
- **THEN** they MUST keep strict `contract_exact_match` and strict `slot_f1` as authoritative public metrics
- **AND** they MUST label `slot_f1_soft`, semantic similarity, structural match, route match, and partial-match views as diagnostic-only
- **AND** they MUST NOT re-score, repair, normalize, replace, or reinterpret existing prediction artifacts as successful strict matches

#### Scenario: Tie tiered diagnosis to next data decisions
- **WHEN** tiered-evaluation design artifacts recommend next work
- **THEN** they MUST connect recommendations to observed residual families, failure-slice counts, route/task errors, safety/confirmation errors, slot mismatches, and data-coverage gaps
- **AND** they MUST NOT recommend another SFT/DPO/GRPO run until a later materialization or readiness phase supplies validated data evidence

#### Scenario: Preserve public-safe tiered-evaluation artifacts
- **WHEN** tiered-evaluation design artifacts are prepared for commit
- **THEN** validation MUST reject raw private rows, absolute local paths, private remote paths, host details, SSH details, secrets, tokens, raw logs, checkpoints, adapters, caches, and oversized generated corpora
