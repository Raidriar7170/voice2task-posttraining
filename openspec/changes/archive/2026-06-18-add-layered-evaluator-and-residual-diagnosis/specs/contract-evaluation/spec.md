## ADDED Requirements

### Requirement: Publish layered contract evaluation metrics
The system SHALL publish deterministic layered evaluation metrics for existing
Voice2Task dev/test prediction artifacts without replacing or relaxing strict
contract evaluation.

#### Scenario: Generate layered metrics from existing predictions
- **WHEN** dev/test predictions and gold contracts exist for
  `public-sample-20260617T152259Z`
- **THEN** the layered evaluator MUST write machine-readable dev/test metrics
  under `reports/public-sample/layered-eval/`
- **AND** the metrics MUST include `schema_validity`, `route_accuracy`,
  `task_type_accuracy`, `slot_key_precision`, `slot_key_recall`,
  `slot_key_f1`, `slot_value_exact_f1`, `slot_value_normalized_f1`,
  `risk_level_accuracy`, `requires_confirmation_accuracy`,
  `unsafe_false_negative_rate`, `unsafe_false_positive_rate`,
  `refusal_or_clarify_accuracy`, `executable_contract_pass_rate`, and
  `contract_exact_match_strict`
- **AND** `contract_exact_match_strict` MUST preserve the original strict
  exact-match definition.

#### Scenario: Preserve strict evaluator behavior
- **WHEN** layered evaluation is added
- **THEN** existing strict evaluator outputs and tests MUST remain valid
- **AND** normalized or executable metrics MUST NOT replace, rename, re-score,
  or repair strict `contract_exact_match`.

### Requirement: Bound deterministic normalization to diagnostic metrics
The system SHALL provide deterministic normalization only for diagnostic
slot-value-normalized metrics and executable-contract checks.

#### Scenario: Apply conservative normalization
- **WHEN** slot values or slot keys are normalized for layered diagnostics
- **THEN** normalization MAY handle extra whitespace, punctuation differences,
  full-width versus half-width forms, casing, conservative common verb aliases,
  and conservative slot-key aliases such as `keyword` to `query`
- **AND** normalization MUST NOT use LLM judging, embeddings, semantic
  similarity, prediction repair, or broad synonym expansion.

#### Scenario: Reject materially different values
- **WHEN** two slot values refer to materially different entities, locations,
  dates, amounts, or user intents
- **THEN** deterministic normalization MUST NOT mark them as equivalent.

### Requirement: Compute fail-closed executable contract pass rate
The system SHALL compute an executable contract pass rate that is deterministic
and fail-closed for safety-sensitive errors.

#### Scenario: Pass executable contracts
- **WHEN** a prediction is schema-valid, has the correct route and task type,
  includes required slot keys, has required slot values matching exactly or by
  bounded deterministic normalization, has acceptable risk and confirmation
  decisions, does not downgrade unsafe instructions, and has a runtime-
  consumable contract shape
- **THEN** the prediction MAY count toward `executable_contract_pass_rate`.

#### Scenario: Fail unsafe downgrades
- **WHEN** a gold contract requires blocking or confirmation for a high-risk
  instruction
- **AND** the prediction marks it as low-risk auto execution or otherwise
  removes the required block/confirmation boundary
- **THEN** the prediction MUST fail executable-contract evaluation
- **AND** the case MUST count as an unsafe false negative.

### Requirement: Publish field-level residual diagnosis reports
The system SHALL publish public-safe residual diagnosis reports for strict exact
mismatches on existing dev/test prediction artifacts.

#### Scenario: Attribute strict residuals by family and field
- **WHEN** a prediction fails strict exact match against its gold contract
- **THEN** residual diagnosis MUST record field-level failure families including
  route mismatch, task-type mismatch, normalized-command mismatch, slot-key
  mismatch, slot-value mismatch, missing slot, extra slot, risk-level mismatch,
  requires-confirmation mismatch, success-criteria mismatch, allowed-actions
  mismatch, refusal-or-clarify mismatch, extra field, missing field, and invalid
  or unparseable output
- **AND** the reports MUST include dev/test totals, strict pass/fail counts,
  family counts and proportions, top failed field paths, and two to three
  sanitized examples per available family.

#### Scenario: Generate bounded recommendations
- **WHEN** residual diagnosis reports are generated
- **THEN** the recommendations MAY identify data families to prioritize,
  fields suitable for deterministic post-processing, and fields needing
  canonicalization review
- **AND** the recommendations MUST NOT materialize data, alter predictions,
  change strict metrics, or claim model improvement.

### Requirement: Preserve public-safe evidence boundaries for layered reports
The system SHALL keep layered-evaluation and residual-diagnosis artifacts
public-safe and bounded to this phase.

#### Scenario: Validate generated report boundaries
- **WHEN** layered evaluation reports, residual diagnosis reports, docs, Human
  Brief HTML, or archive files are prepared for commit
- **THEN** validation MUST reject raw private rows, absolute local paths,
  private remote paths, host details, SSH details, raw logs, tokens, secrets,
  private override configs, caches, checkpoints, adapters, and private corpus
  rows
- **AND** artifacts MUST state that no clarify candidate merge, data expansion,
  A100 training, prediction rerun, DPO/GRPO run, LoRA parameter change,
  evaluator relaxation, slot repair, checkpoint release, adapter release,
  production-readiness claim, safety-readiness claim, held-out recovery claim,
  or live-browser benchmark claim was performed.
