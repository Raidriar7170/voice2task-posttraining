## ADDED Requirements

### Requirement: Publish current tiny-adapter held-out prediction evidence
The system SHALL publish public-safe evidence for the current-manifest tiny
adapter's held-out prediction-only diagnostic, reporting `dev` and `test`
contract metrics separately and comparing them with the prior train-internal
tiny-overfit result without broad recovery claims.

#### Scenario: Generate split-specific current tiny held-out metrics
- **WHEN** sanitized current tiny-adapter predictions are available for `dev` and `test`
- **THEN** the evidence pack MUST include split-specific predictions, gold rows, strict metrics, schema diagnostics, alignment diagnostics, constrained decoding diagnostics, prompt snapshots, raw decoded summaries, generation traces, and prediction metadata

#### Scenario: Generate combined current tiny held-out manifest and report
- **WHEN** split-specific evidence has been generated
- **THEN** the combined manifest and report MUST record dataset manifest ID, base model, adapter source kind, prior train-internal exact match, each split's prediction count, `contract_exact_match`, `slot_f1`, schema-valid count, residual rows, artifact links, and bounded overall interpretation

#### Scenario: Bound current tiny held-out interpretation
- **WHEN** public documentation or Human Briefs describe the current tiny held-out result
- **THEN** they MUST state that this is prediction-only public-sample held-out diagnosis
- **AND** they MUST NOT claim new training, DPO, checkpoint release, adapter release, model recovery, private-corpus generalization, production readiness, public full-corpus release, or live-browser benchmark improvement

#### Scenario: Validate current tiny held-out evidence boundaries
- **WHEN** current tiny held-out diagnostic evidence is prepared for commit
- **THEN** leak-scan validation MUST reject raw private rows, local or remote private paths, secrets, private IP addresses, SSH details, raw logs, checkpoints, adapters, caches, oversized generated corpora, model snapshots, and private remote paths
