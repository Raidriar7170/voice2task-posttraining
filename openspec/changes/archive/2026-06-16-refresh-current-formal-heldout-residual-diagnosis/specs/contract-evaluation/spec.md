## ADDED Requirements

### Requirement: Refresh current formal residual decision evidence
The system SHALL keep the committed formal held-out residual-family diagnosis,
residual-cluster inspection, and formal remediation target-selection artifacts
aligned with the latest formal public held-out prediction evidence boundary.

#### Scenario: Refresh residual-family diagnosis from current evidence
- **WHEN** a newer formal public held-out prediction evidence pack is selected
  as the current public-facing truth surface
- **THEN** the formal residual-family diagnosis artifact MUST record that
  evidence pack's manifest id, strict metrics, split row counts, and diagnosis
  boundary
- **AND** it MUST NOT read from or report an older manifest as current

#### Scenario: Refresh target selection from refreshed diagnosis
- **WHEN** formal remediation target-selection evidence is regenerated
- **THEN** it MUST read the refreshed residual-family diagnosis artifact
- **AND** it MUST carry forward the same source manifest id and strict metrics
- **AND** it MUST preserve the boundary that target selection is not training,
  not data generation, not prediction repair, and not evaluator relaxation

#### Scenario: Refresh residual-cluster inspection from refreshed diagnosis
- **WHEN** formal residual-cluster inspection evidence is regenerated
- **THEN** it MUST read the refreshed residual-family diagnosis artifact
- **AND** it MUST carry forward the same source manifest id, strict metrics,
  residual row counts, and residual field counts
- **AND** it MUST preserve the boundary that cluster inspection does not
  authorize data, training, prompt, prediction, or evaluator changes

#### Scenario: Refresh coverage current-evidence lineage without rewriting legacy provenance
- **WHEN** downstream form-fill confirmation-marker coverage evidence references
  the refreshed residual-cluster inspection as current residual evidence
- **THEN** it MUST record the refreshed formal held-out manifest id for that
  current residual evidence source
- **AND** it MUST preserve legacy policy, coverage-extension, materialized
  candidate, and formal public sample provenance instead of rewriting those
  historical sources to the newer manifest

#### Scenario: Validate refreshed public evidence boundaries
- **WHEN** refreshed residual diagnosis, target-selection reports, or companion
  Human Briefs are prepared for commit
- **THEN** validation MUST reject raw private rows, absolute local paths, private
  remote paths, host details, SSH details, secrets, tokens, raw logs,
  checkpoints, adapters, caches, and oversized generated corpora
- **AND** public summaries MUST keep strict `contract_exact_match` and strict
  `slot_f1` authoritative while labeling `slot_f1_soft` as diagnostic only
