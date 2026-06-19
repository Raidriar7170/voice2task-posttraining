# slot-canonicalization-policy Specification

## Purpose
Define public-safe slot key, slot value, normalized-command, and
model/postprocessor boundary policy evidence for Voice2Task before later
candidate materialization, deterministic postprocessor work, or training retry
phases.
## Requirements
### Requirement: Publish slot canonicalization policy evidence
The system SHALL publish public-safe slot canonicalization policy evidence from
committed public evaluation, residual diagnosis, schema, and dataset artifacts
before rematerializing canonical slot data, adding a deterministic contract
postprocessor, or launching another training phase.

#### Scenario: Generate required policy artifacts
- **WHEN** the slot canonicalization policy phase is applied
- **THEN** it MUST write `summary.md`, `summary.json`,
  `slot-key-policy.md`, `slot-value-policy.md`,
  `normalized-command-policy.md`, `model-target-boundary.md`, and
  `recommended-next-change.md` under
  `reports/public-sample/slot-canonicalization-policy/`
- **AND** the artifacts MUST cite the current committed evidence sources used
  for the policy.

#### Scenario: Define deterministic slot key boundaries
- **WHEN** the slot key policy is written
- **THEN** it MUST list canonical slot keys, alias-to-canonical mappings,
  disallowed slot keys, task-type-specific required and optional slot keys,
  missing-slot and extra-slot handling guidance, and public-safe examples
- **AND** it MUST distinguish task-scoped aliases from non-equivalent fields
  that must not be merged.

#### Scenario: Define conservative slot value boundaries
- **WHEN** the slot value policy is written
- **THEN** it MUST list safe value canonicalization types, non-equivalence
  cases, Chinese filler handling, punctuation/space/full-width/half-width/case
  handling, common verb/request-word handling, numeric/date/price/city/product
  name/URL/email/phone boundaries, and examples
- **AND** it MUST state that slot-value normalization is design and diagnostic
  guidance only and does not affect strict exact-match scoring.

#### Scenario: Reposition normalized command
- **WHEN** the normalized-command policy is written
- **THEN** it MUST document the current problem, proposed diagnostic/display
  positioning, examples, metric impact, and non-goals
- **AND** it MUST evaluate whether `normalized_command` should remain a model
  target, be generated from deterministic templates, and remain outside the
  core executable-contract pass condition.

#### Scenario: Separate model targets from derived fields
- **WHEN** the model-target boundary is written
- **THEN** it MUST classify model-predicted fields separately from
  deterministic postprocessor-derived or validated fields
- **AND** it MUST explain why freely generating derivable fields such as
  `allowed_actions`, `success_criteria`, display `normalized_command`, policy
  tags, confirmation defaults, or runtime hints can enlarge the output space and
  lower strict exact or executable-contract pass rates.

#### Scenario: Recommend a bounded next phase
- **WHEN** the policy summary is complete
- **THEN** `recommended-next-change.md` MUST include a proposed next change id,
  rationale, scope, acceptance criteria, non-goals, metrics to watch, and claims
  not to overstate
- **AND** it MUST NOT implement the next phase.

#### Scenario: Preserve design-only and public-safe boundaries
- **WHEN** slot canonicalization policy artifacts, docs, Human Brief HTML, or
  archive files are prepared for commit
- **THEN** validation MUST reject raw private rows, absolute local paths,
  private remote paths, host details, SSH details, raw logs, tokens, secrets,
  checkpoints, adapters, caches, and private corpus rows
- **AND** this phase MUST NOT train, predict, mutate data, change splits, change
  evaluator definitions, relax strict exact, use an LLM judge, perform semantic
  equivalence scoring, repair predictions, publish checkpoints or adapters,
  claim model improvement, claim held-out recovery, claim production readiness,
  claim safety readiness, or claim live-browser benchmark improvement.

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

### Requirement: Review canonical slot-boundary candidates before formal merge
The system SHALL review standalone canonical slot-boundary candidates before
any later formal public sample merge, generated SFT/DPO artifact change,
deterministic postprocessor implementation, prediction rerun, or training
phase.

#### Scenario: Generate review-only artifacts
- **WHEN** the canonical slot-boundary candidate review phase is applied
- **THEN** it MUST write machine-readable review evidence and a
  human-readable summary under
  `reports/public-sample/canonical-slot-boundary-candidate-review/`
- **AND** the output MUST cite
  `reports/public-sample/canonical-slot-boundary-candidates/summary.json` as
  its source candidate materialization evidence.

#### Scenario: Classify candidate classes without immediate merge approval
- **WHEN** candidate classes are reviewed
- **THEN** slot-key alias and conservative slot-value boundary classes MAY be
  marked `eligible_for_later_formal_merge_proposal`
- **AND** every reviewed class MUST keep
  `approved_for_formal_merge_now=false` and
  `requires_separate_openspec_change=true`.

#### Scenario: Preserve normalized-command diagnostic boundary
- **WHEN** normalized-command display examples are reviewed
- **THEN** they MUST be classified as `diagnostic_display_only`
- **AND** they MUST NOT declare equivalence, alter strict exact, alter
  executable-contract pass conditions, rescore prior residuals, or repair
  predictions.

#### Scenario: Preserve non-equivalence exclusions
- **WHEN** excluded non-equivalence examples are reviewed
- **THEN** they MUST remain classified as
  `blocked_or_deferred_non_equivalence`
- **AND** the review MUST NOT loosen date, city/location, product, URL host,
  price/amount, query/product, location/destination, or action/reason
  boundaries.

#### Scenario: Preserve review-only execution boundary
- **WHEN** review evidence is generated
- **THEN** it MUST state and machine-record that formal public sample seed
  traces, SFT rows, DPO pairs, manifests, train/dev/test splits, evaluator
  definitions, predictions, and model artifacts remain unchanged
- **AND** it MUST NOT generate JSONL seed candidates, generate SFT/DPO rows,
  rebuild a manifest, train, predict, run on A100, implement a deterministic
  postprocessor, relax strict exact, use an LLM judge, perform
  semantic-equivalence scoring, repair predictions, or claim model
  improvement.

#### Scenario: Validate public-safe review artifacts
- **WHEN** review artifacts, docs, Human Brief HTML, or archive files are
  prepared for commit
- **THEN** validation MUST reject raw private rows, absolute local paths,
  private remote paths, host details, SSH details, raw logs, tokens, secrets,
  checkpoints, adapters, caches, and private corpus rows
- **AND** the source candidate materialization artifacts and the stale active
  `merge-scaled-clarify-slot-boundary-candidates` change MUST remain
  unmodified unless a separate bounded phase explicitly owns them.
