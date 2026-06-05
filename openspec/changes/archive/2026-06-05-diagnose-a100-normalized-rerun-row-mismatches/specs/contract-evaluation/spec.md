## ADDED Requirements

### Requirement: Publish normalized-command rerun row-mismatch diagnosis evidence
The system SHALL publish public-safe row-level mismatch diagnosis evidence for the A100 normalized-command policy train-split rerun without changing source predictions, prompt behavior, decoding behavior, schema behavior, parser behavior, retry behavior, evaluator metrics, or source strict metric interpretation.

#### Scenario: Derive row-level mismatch diagnosis from prior public artifacts
- **WHEN** the diagnosis is generated
- **THEN** it MUST derive only from `reports/public-sample/a100-normalized-command-policy-train-split-rerun/` public-safe artifacts
- **AND** it MUST record `diagnostic_kind=a100_normalized_rerun_row_mismatch_diagnosis`
- **AND** it MUST preserve source strict metrics including `json_valid_rate=1/3`, `contract_exact_match=0.0`, `task_type_accuracy=0.0`, `route_accuracy=0.0`, `confirmation_accuracy=1/3`, and `slot_f1=0.0`

#### Scenario: Classify residual rows without repairing predictions
- **WHEN** row-level failures are reported
- **THEN** the diagnosis MUST report all three train rows and classify the primary failure families as one missing `confirmation_required` schema failure, one invalid `task_type` enum schema failure, and one schema-valid task/route/safety/slot mismatch
- **AND** invalid predictions MUST remain invalid
- **AND** field-level mismatches MUST remain visible for reviewer inspection

#### Scenario: Bound row-level diagnosis claims
- **WHEN** evidence, Human Briefs, loop reports, or archived OpenSpec artifacts describe the row-mismatch diagnosis
- **THEN** they MUST NOT claim A100 execution in this phase, training, prediction rerun, prompt change, decoding change, schema change, parser change, retry change, evaluator metric change, prediction repair, prediction replacement, prediction re-score, semantic-equivalence scoring, normalized-command normalization, checkpoint release, adapter release, held-out generalization, production readiness, public full-corpus release, model-quality improvement, or live-browser benchmark improvement

#### Scenario: Keep row-level diagnosis public-safe
- **WHEN** diagnosis artifacts are prepared for commit
- **THEN** leak-scan validation MUST reject raw private rows, local or remote private paths, secrets, private IP addresses, SSH details, raw logs, checkpoints, adapters, caches, oversized generated corpora, and private remote paths
