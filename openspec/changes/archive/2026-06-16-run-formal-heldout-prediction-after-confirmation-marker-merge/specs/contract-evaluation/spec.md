## ADDED Requirements

### Requirement: Publish post-confirmation-marker-merge formal held-out prediction evidence
The system SHALL publish public-safe prediction-only evidence for the formal public sample after confirmation-marker extension candidates have been merged, while preserving the changed manifest boundary.

#### Scenario: Evaluate current post-merge formal held-out splits
- **WHEN** sanitized private-adapter predictions are available for the current formal public sample dev and test splits after the confirmation-marker extension merge
- **THEN** the system MUST evaluate them with the existing strict contract ladder, including `json_valid_rate`, `task_type_accuracy`, `route_accuracy`, `safety_precision`, `safety_recall`, `confirmation_accuracy`, `slot_f1`, `slot_f1_soft`, and `contract_exact_match`
- **AND** the evidence MUST record manifest id `public-sample-20260616T074315Z`, 69 dev SFT rows, 69 test SFT rows, and the source formal sample counts of 98 seed rows, 252 SFT rows, and 850 DPO pairs

#### Scenario: Preserve boundary-changed comparison semantics
- **WHEN** reports or Human Briefs describe post-confirmation-marker-merge held-out prediction metrics
- **THEN** they MUST publish those metrics in a distinct evidence directory from the earlier formal held-out prediction evidence
- **AND** they MUST state that prior formal held-out metrics used a different public sample boundary and are not a clean direct improvement/regression comparison

#### Scenario: Preserve prediction-only and public-safety boundaries
- **WHEN** post-confirmation-marker-merge held-out prediction evidence is prepared for commit
- **THEN** committed artifacts MUST state that no SFT training, DPO training, GRPO training, dataset mutation, evaluator relaxation, semantic-equivalence scoring, slot normalization, prediction repair, prediction replacement, or prediction re-score was performed
- **AND** committed artifacts MUST NOT claim held-out recovery, model recovery, checkpoint release, adapter release, production readiness, public full-corpus release, private-corpus generalization, or live-browser benchmark improvement
- **AND** leak-scan validation MUST reject raw private rows, absolute local paths, private remote paths, host details, SSH details, secrets, tokens, raw logs, checkpoints, adapters, caches, and oversized generated corpora

#### Scenario: Record blocked prediction execution safely
- **WHEN** the prediction-only A100 run cannot safely execute because the private adapter, private override, remote dependency, or idle GPU state is unavailable
- **THEN** the evidence MUST record a blocked status without writing fabricated predictions or model-quality metrics
- **AND** committed artifacts MUST omit raw logs, host details, SSH details, private paths, checkpoints, adapters, caches, tokens, and private corpus rows
