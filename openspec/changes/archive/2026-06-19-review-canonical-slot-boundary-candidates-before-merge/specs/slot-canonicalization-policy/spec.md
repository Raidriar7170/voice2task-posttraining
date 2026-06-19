## ADDED Requirements

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
