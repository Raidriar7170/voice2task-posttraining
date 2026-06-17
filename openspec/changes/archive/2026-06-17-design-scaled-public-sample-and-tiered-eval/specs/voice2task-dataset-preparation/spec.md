## ADDED Requirements

### Requirement: Design scaled public sample before materialization
The system SHALL publish a public-safe design artifact before expanding the formal public sample beyond the current manifest boundary.

#### Scenario: Produce scale-up target distribution
- **WHEN** a scaled public-sample design phase runs
- **THEN** it MUST report the current manifest id, current seed/SFT/DPO counts, current train/dev/test split counts, target seed-count milestone, and target family distribution
- **AND** it MUST identify task families, routes, safety reasons, confirmation behaviors, slot-key shapes, and accepted/rejected target-shape coverage that need additional examples

#### Scenario: Preserve design-only boundary
- **WHEN** scaled public-sample design evidence is generated
- **THEN** it MUST NOT mutate seed traces, SFT rows, DPO rows, manifests, model configs, prompts, evaluator metrics, prediction artifacts, or private corpora
- **AND** it MUST NOT claim model recovery, safety improvement, production readiness, checkpoint release, adapter release, private-corpus generalization, or live-browser benchmark improvement

#### Scenario: Keep future materialization reviewable
- **WHEN** the design recommends future data generation
- **THEN** it MUST separate candidate family names, accepted contract sketches, rejected drift sketches, augmentation-depth guidance, and validation gates so a later materialization phase can be reviewed before writing public sample files

#### Scenario: Preserve public-safe design artifacts
- **WHEN** scaled public-sample design artifacts are prepared for commit
- **THEN** validation MUST reject raw private rows, absolute local paths, private remote paths, host details, SSH details, secrets, tokens, raw logs, checkpoints, adapters, caches, and oversized generated corpora
