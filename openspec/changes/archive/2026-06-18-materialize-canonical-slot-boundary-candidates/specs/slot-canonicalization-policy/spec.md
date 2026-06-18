## ADDED Requirements

### Requirement: Materialize canonical slot-boundary candidates as standalone evidence
The system SHALL materialize public-safe canonical slot-boundary candidate
examples from the archived slot canonicalization policy without mutating formal
public sample data, generated SFT/DPO artifacts, split boundaries, evaluator
definitions, or model outputs.

#### Scenario: Generate standalone candidate artifacts
- **WHEN** the canonical slot-boundary candidate phase is applied
- **THEN** it MUST write machine-readable candidate evidence and a human-readable
  summary under `reports/public-sample/canonical-slot-boundary-candidates/`
- **AND** the output MUST cite
  `reports/public-sample/slot-canonicalization-policy/` as its source policy
  evidence.

#### Scenario: Preserve traceability to source policy
- **WHEN** candidate groups are generated
- **THEN** each accepted candidate MUST include a candidate id, source policy
  section, input slot sketch, canonical slot sketch, task type, rationale,
  review status, and later allowed operation
- **AND** the report MUST include separate excluded non-equivalence examples
  that remain outside accepted candidates.

#### Scenario: Preserve standalone materialization boundary
- **WHEN** candidate evidence is generated
- **THEN** it MUST state and machine-record that formal public sample seed
  traces, SFT rows, DPO pairs, manifests, train/dev/test splits, evaluator
  definitions, predictions, and model artifacts remain unchanged
- **AND** it MUST NOT generate SFT/DPO rows, rebuild a manifest, train, predict,
  run on A100, implement a deterministic postprocessor, relax strict exact, use
  an LLM judge, perform semantic-equivalence scoring, repair predictions, or
  claim model improvement.

#### Scenario: Keep normalized-command candidates diagnostic only
- **WHEN** normalized-command examples are included
- **THEN** they MUST be marked as display or diagnostic candidates only
- **AND** they MUST NOT be used to declare equivalence, change strict exact,
  change executable-contract pass conditions, or re-score prior residuals.

#### Scenario: Validate public-safe standalone artifacts
- **WHEN** candidate artifacts, docs, Human Brief HTML, or archive files are
  prepared for commit
- **THEN** validation MUST reject raw private rows, absolute local paths,
  private remote paths, host details, SSH details, raw logs, tokens, secrets,
  checkpoints, adapters, caches, and private corpus rows
- **AND** the previously archived slot policy artifacts and the stale active
  `merge-scaled-clarify-slot-boundary-candidates` change MUST remain
  unmodified unless a separate bounded phase explicitly owns them.
