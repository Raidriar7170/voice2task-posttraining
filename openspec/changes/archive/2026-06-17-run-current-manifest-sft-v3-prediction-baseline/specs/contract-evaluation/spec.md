## ADDED Requirements

### Requirement: Publish current-manifest SFT v3 prediction-only baseline evidence
The system SHALL publish public-safe prediction-only evidence for the existing private SFT v3 adapter on the current formal public sample manifest after the blocked-payment repair materialization.

#### Scenario: Evaluate current-manifest SFT v3 dev/test predictions
- **WHEN** sanitized private SFT v3 adapter predictions are available for the current formal public sample dev and test splits
- **THEN** the system MUST evaluate them with the existing strict contract ladder, including `json_valid_rate`, `task_type_accuracy`, `route_accuracy`, `safety_precision`, `safety_recall`, `confirmation_accuracy`, `slot_f1`, `slot_f1_soft`, and `contract_exact_match`
- **AND** the evidence MUST record manifest id `public-sample-20260616T165835Z`, 69 dev SFT rows, 69 test SFT rows, and the current source counts of 100 seed rows, 256 SFT rows, and 864 DPO pairs

#### Scenario: Preserve current-manifest comparison boundary
- **WHEN** reports or Human Briefs describe current-manifest SFT v3 prediction-only metrics
- **THEN** they MUST state that previous SFT v3 metrics were bound to `public-sample-20260616T074315Z`
- **AND** they MUST NOT present old/new values as a clean improvement or regression unless the manifest boundary is explicitly called out

#### Scenario: Record source adapter runtime accurately
- **WHEN** the prediction-only evidence is generated with the existing SFT v3 private adapter
- **THEN** the report and manifest MUST record `source_adapter_runtime` as `a100-form-fill-remediation-sft-v3`
- **AND** they MUST NOT imply that the older merged-slot-value adapter produced the metrics

#### Scenario: Preserve prediction-only and public-safety boundaries
- **WHEN** current-manifest SFT v3 prediction-only evidence is prepared for commit
- **THEN** committed artifacts MUST state that no SFT training, DPO training, GRPO training, dataset mutation, evaluator relaxation, semantic-equivalence scoring, slot normalization, prediction repair, prediction replacement, or prediction re-score was performed
- **AND** committed artifacts MUST NOT claim held-out recovery, model recovery, checkpoint release, adapter release, production readiness, public full-corpus release, private-corpus generalization, or live-browser benchmark improvement
- **AND** leak-scan validation MUST reject raw private rows, absolute local paths, private remote paths, host details, SSH details, secrets, tokens, raw logs, checkpoints, adapters, caches, and oversized generated corpora

#### Scenario: Record blocked prediction execution safely
- **WHEN** the prediction-only A100 run cannot safely execute because the private adapter, private override, remote dependency, or idle GPU state is unavailable
- **THEN** the evidence MUST record a blocked status without writing fabricated predictions or model-quality metrics
- **AND** committed artifacts MUST omit raw logs, host details, SSH details, private paths, checkpoints, adapters, caches, tokens, and private corpus rows
