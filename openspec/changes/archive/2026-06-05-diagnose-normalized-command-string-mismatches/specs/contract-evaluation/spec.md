## ADDED Requirements

### Requirement: Publish confirmation-rerun normalized-command string-mismatch diagnosis evidence
The system SHALL publish public-safe normalized-command string-mismatch diagnosis evidence for the confirmation-required train-split rerun without changing source predictions, prompt behavior, decoding behavior, or evaluator metrics.

#### Scenario: Derive normalized-command diagnosis from row-mismatch evidence
- **WHEN** the diagnosis is generated from committed confirmation-rerun row-mismatch evidence
- **THEN** it MUST report `normalized_command` mismatch rows, aggregate mismatch counts, source artifact links, and strict metrics inherited from the source evidence

#### Scenario: Separate string mismatch contexts
- **WHEN** the report explains why `normalized_command` contributes to strict exact-match failures
- **THEN** it MUST distinguish strict string-only mismatch, mismatch co-occurring with schema required-field failure, and mismatch co-occurring with task/route/safety semantic mismatch

#### Scenario: Preserve strict evaluator interpretation
- **WHEN** normalized-command differences are reported
- **THEN** the diagnosis MUST NOT normalize, repair, coerce, replace, semantically score, mark equivalent, or re-score prediction fields or evaluator metrics

#### Scenario: Bound normalized-command diagnosis claims
- **WHEN** evidence, Human Briefs, loop reports, or archived OpenSpec artifacts describe the normalized-command diagnosis
- **THEN** they MUST state that the phase is local evidence-only analysis and MUST NOT claim A100 rerun recovery, held-out generalization, checkpoint release, adapter release, production readiness, public full-corpus release, model-quality improvement, or live-browser benchmark improvement

#### Scenario: Keep normalized-command diagnosis public-safe
- **WHEN** normalized-command diagnosis artifacts are prepared for commit
- **THEN** leak-scan validation MUST reject raw private rows, local or remote private paths, secrets, private IP addresses, SSH details, raw logs, checkpoints, adapters, model caches, oversized generated corpora, and private remote paths
