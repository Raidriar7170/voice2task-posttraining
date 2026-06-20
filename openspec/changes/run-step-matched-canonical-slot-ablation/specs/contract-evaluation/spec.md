## ADDED Requirements

### Requirement: Verify step-matched ablation comparison boundary
The system SHALL verify from concrete artifacts that the control and treatment
manifests have comparable frozen dev/test inputs and gold contracts before any
step-matched causal comparison is interpreted.

#### Scenario: Discover and compare formal manifest boundaries
- **WHEN** the step-matched canonical slot ablation starts
- **THEN** the system MUST discover the pre-canonical and post-canonical formal
  public-sample manifests, train split counts, dev/test gold files, gold
  Browser Task Contracts, and canonical train-only data lineage from repository
  artifacts rather than relying only on `CONTEXT.md`
- **AND** it MUST compute dev/test row id hashes, row order hashes, input
  content hashes, per-row gold contract hashes, and combined gold content
  hashes for both manifests
- **AND** it MUST write
  `reports/public-sample/step-matched-canonical-slot-ablation/boundary-verification.json`
  with the comparison method, counts, hashes, equality result, and
  interpretation.

#### Scenario: Block mismatched held-out boundaries
- **WHEN** dev/test rows, stable ids, inputs, or gold contracts cannot be
  proven identical or safely aligned by stable sample id with identical gold
  contracts
- **THEN** the system MUST stop before training, write blocked evidence, and
  recommend establishing a shared frozen held-out set
- **AND** it MUST NOT treat matching split counts as proof of comparable
  held-out samples.

### Requirement: Evaluate step-matched canonical slot SFT ablation
The system SHALL evaluate fresh step-matched control and treatment SFT adapters
on the same frozen dev/test boundary and publish public-safe comparison
artifacts.

#### Scenario: Report primary and guardrail metrics
- **WHEN** control and treatment predictions are available for the frozen
  dev/test rows
- **THEN** the system MUST write separate control and treatment dev/test metrics
  for `contract_exact_match_strict`, `strict_slot_f1`,
  `slot_value_exact_f1`, `slot_value_normalized_f1`,
  `executable_contract_pass_rate`, `schema_validity`, `json_valid_rate`,
  `route_accuracy`, `task_type_accuracy`, `safety_recall`,
  `unsafe_false_negative_rate`, `unsafe_false_positive_rate`,
  `requires_confirmation_accuracy`, and `refusal_or_clarify_accuracy`
- **AND** it MUST preserve the existing evaluator semantics without prediction
  repair, semantic-equivalence substitution, slot normalization as a scoring
  replacement, LLM judging, or evaluator relaxation.

#### Scenario: Publish paired row and family deltas
- **WHEN** both arms have evaluated dev/test metrics
- **THEN** the system MUST align control, treatment, and gold rows by sample id
  or verified row order and write `paired-row-analysis.json` with exact
  recoveries/regressions, executable recoveries/regressions, slot
  recoveries/regressions, safety recoveries/regressions, and confirmation
  recoveries/regressions
- **AND** it MUST write `family-level-deltas.json` with top deltas by task
  family, route family, task type, and relevant slot-boundary family.

#### Scenario: Publish bootstrap diagnostics without significance overclaim
- **WHEN** paired row analysis is available
- **THEN** the system MUST run a fixed-seed paired bootstrap diagnostic for
  binary metric deltas and sample-level F1 deltas and write
  `bootstrap-analysis.json` with bootstrap seed, resample count, intervals, and
  interpretation
- **AND** it MUST NOT call the one-seed result statistically significant or
  sufficient for public release.

#### Scenario: Apply the fixed pilot gate
- **WHEN** comparison metrics are available for the fixed random seed
- **THEN** the system MUST write `comparison.json`, `comparison.md`, and
  `decision.md` with absolute treatment-minus-control deltas for dev and test,
  answers to the required comparison questions, and exactly one decision label:
  `PASS_STEP_MATCHED_PILOT`, `POSITIVE_BUT_INCONCLUSIVE`,
  `NO_CANONICAL_DATA_SIGNAL`, or `REGRESSION_OR_GUARDRAIL_FAILURE`
- **AND** it MUST recommend three-seed confirmation only if dev and test both
  improve `slot_value_exact_f1` by at least `0.03`, dev and test both improve
  `executable_contract_pass_rate` by at least `0.02`, `safety_recall` does not
  drop, `unsafe_false_negative_rate` does not increase,
  `requires_confirmation_accuracy` drops by no more than `0.01`, and
  `schema_validity` and `json_valid_rate` do not drop
- **AND** if the gate fails it MUST NOT recommend adding small canonical
  candidates or running DPO as the next step.

#### Scenario: Keep public claims bounded
- **WHEN** step-matched comparison artifacts, Human Brief HTML, status docs, or
  OpenSpec archive artifacts are prepared for commit
- **THEN** validation MUST reject raw private rows, absolute local paths,
  private remote paths, host details, SSH details, tokens, secrets, raw logs,
  private override configs, caches, checkpoints, adapters, and private corpus
  rows
- **AND** public summaries MUST NOT claim public adapter release, checkpoint
  release, production readiness, safety certification, live-browser benchmark
  improvement, or held-out recovery beyond the observed strict metrics.
