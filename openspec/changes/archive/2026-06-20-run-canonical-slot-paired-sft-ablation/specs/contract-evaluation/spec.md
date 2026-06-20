## ADDED Requirements

### Requirement: Verify paired ablation held-out boundary
The system SHALL verify that the control and treatment manifests share the same
frozen dev/test held-out rows, order, and gold contracts before causal SFT
comparison is interpreted.

#### Scenario: Compare held-out content hashes
- **WHEN** the ablation starts with control manifest
  `public-sample-20260617T152259Z` and treatment manifest
  `public-sample-20260619T090925Z`
- **THEN** the system MUST compute dev and test gold content hashes for both
  manifests and compare row ids, row order, and gold Browser Task Contracts
- **AND** it MUST write
  `reports/public-sample/canonical-slot-paired-sft-ablation/boundary-verification.json`
  with the hash inputs, split counts, equality result, and interpretation

#### Scenario: Block mismatched held-out boundary
- **WHEN** any dev/test row id, order, gold contract, or content hash differs
  between control and treatment
- **THEN** the system MUST stop the causal experiment, write blocked evidence,
  and recommend establishing a shared frozen held-out set
- **AND** it MUST NOT train paired adapters, report causal deltas, or treat
  equal split counts as proof of comparable held-out samples

### Requirement: Evaluate canonical slot-boundary paired SFT ablation
The system SHALL evaluate the fresh control and treatment SFT adapters on the
same frozen dev/test boundary and publish public-safe comparison artifacts.

#### Scenario: Report strict primary and guardrail metrics
- **WHEN** control and treatment predictions are available for frozen dev/test
- **THEN** the system MUST report dev and test metrics for
  `contract_exact_match_strict`, `slot_value_exact_f1`,
  `slot_value_normalized_f1`, `executable_contract_pass_rate`,
  `schema_validity`, `route_accuracy`, `task_type_accuracy`, `safety_recall`,
  `unsafe_false_negative_rate`, `requires_confirmation_accuracy`, and
  `json_valid_rate`
- **AND** it MUST write control and treatment evidence under
  `reports/public-sample/canonical-slot-paired-sft-ablation/control/` and
  `reports/public-sample/canonical-slot-paired-sft-ablation/treatment/`

#### Scenario: Publish comparison deltas and regressions
- **WHEN** both arms have evaluated metrics
- **THEN** the system MUST write
  `reports/public-sample/canonical-slot-paired-sft-ablation/comparison.json`
  and `reports/public-sample/canonical-slot-paired-sft-ablation/comparison.md`
  with absolute deltas computed as treatment minus control, dev/test split
  separation, top family-level deltas, exact recoveries and regressions, slot
  recoveries and regressions, and safety or confirmation regressions

#### Scenario: Apply one-seed pilot gate
- **WHEN** comparison metrics are available for the fixed random seed
- **THEN** the system MUST recommend later three-seed confirmation only if
  treatment improves dev and test `slot_value_exact_f1` by at least `0.03`,
  improves dev and test `executable_contract_pass_rate` by at least `0.02`,
  does not reduce `safety_recall`, does not increase unsafe false negatives,
  and reduces confirmation accuracy by no more than `0.01`
- **AND** if the gate fails it MUST recommend
  `design-and-implement-contract-v2` and MUST NOT recommend adding small
  canonical candidates or running DPO as the next step

#### Scenario: Keep public claims bounded
- **WHEN** comparison artifacts, Human Brief HTML, status docs, or OpenSpec
  archive artifacts are prepared for commit
- **THEN** validation MUST reject raw private rows, absolute local paths,
  private remote paths, host details, SSH details, tokens, secrets, raw logs,
  private override configs, caches, checkpoints, adapters, and private corpus
  rows
- **AND** public summaries MUST NOT claim public adapter release, checkpoint
  release, production readiness, live-browser benchmark improvement, or
  held-out recovery beyond the observed strict metrics
