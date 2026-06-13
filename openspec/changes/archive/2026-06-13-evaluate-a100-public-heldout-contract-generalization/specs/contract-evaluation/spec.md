## ADDED Requirements

### Requirement: Publish public held-out contract generalization evidence
The system SHALL publish public-safe A100 held-out diagnostic evidence that reports public `dev` and `test` contract metrics separately and bounds interpretation.

#### Scenario: Generate split-specific held-out metrics
- **WHEN** sanitized public held-out predictions are available for `dev` and `test`
- **THEN** the evidence pack MUST include split-specific predictions, gold rows, strict metrics, schema diagnostics, alignment diagnostics, constrained decoding diagnostics, prompt snapshots, raw decoded summaries, generation traces, and prediction metadata

#### Scenario: Generate combined held-out manifest and report
- **WHEN** split-specific evidence has been generated
- **THEN** the combined manifest and report MUST record each split's prediction count, `contract_exact_match`, `slot_f1`, schema-valid count, residual rows, artifact links, and a bounded overall interpretation

#### Scenario: Bound held-out interpretation
- **WHEN** public documentation or Human Briefs describe the held-out result
- **THEN** they MUST state that public `dev`/`test` evidence does not prove private-corpus generalization, checkpoint release, adapter release, production readiness, or live-browser benchmark improvement

#### Scenario: Validate held-out evidence boundaries
- **WHEN** held-out diagnostic evidence is prepared for commit
- **THEN** leak-scan validation MUST reject raw private rows, local or remote private paths, secrets, private IP addresses, SSH details, raw logs, checkpoints, adapters, caches, oversized generated corpora, and private remote paths
