## ADDED Requirements

### Requirement: Run step-matched canonical slot SFT ablation
The system SHALL support a bounded one-seed step-matched SFT ablation that
trains fresh control and treatment LoRA adapters to isolate the effect of
reviewed canonical slot-boundary train-only data from unequal optimizer-step
budgets.

#### Scenario: Derive a unified optimizer-step budget
- **WHEN** the step-matched ablation is prepared
- **THEN** the system MUST recover the previous paired control run's training
  budget from actual trainer state, actual training summary, or an exact
  reconstruction from the prior control config, train-row count, batch size,
  gradient accumulation, and epoch count
- **AND** it MUST record the source as observed or reconstructed in
  `reports/public-sample/step-matched-canonical-slot-ablation/*/training-summary.json`
- **AND** it MUST block before training if the previous control optimizer-step
  budget cannot be verified honestly.

#### Scenario: Train fresh step-matched adapters
- **WHEN** boundary verification passes, the optimizer-step budget is verified,
  A100 execution is reachable, and an idle GPU can be selected safely
- **THEN** the system MUST train a fresh control adapter on the pre-canonical
  formal public-sample train SFT rows and a fresh treatment adapter on the
  post-canonical formal public-sample train SFT rows
- **AND** both arms MUST use the same explicit `max_steps`, effective batch
  size, scheduler step count, random seed, prompt template, tokenizer, decoding
  policy, evaluator, LoRA rank, LoRA alpha, LoRA dropout, learning rate, base
  model, and frozen dev/test inputs
- **AND** the system MUST NOT reuse an older adapter as the step-matched
  control or treatment adapter.

#### Scenario: Record step and token exposure honestly
- **WHEN** either arm finishes training
- **THEN** its public-safe training summary MUST record configured `max_steps`,
  observed optimizer/global steps when available, effective batch size,
  train-row count, theoretical examples seen, scheduler step count,
  target-token exposure when available, random seed, LoRA policy, base model,
  manifest id, and release status
- **AND** it MUST state that the run is step-matched, not token-matched, when
  target-token exposure differs between arms.

#### Scenario: Restrict the ablation to SFT only
- **WHEN** the step-matched canonical slot ablation runs
- **THEN** the system MUST NOT run DPO, GRPO, an LLM judge, prediction repair,
  semantic-equivalence scoring, evaluator relaxation, Contract V2
  implementation, new canonical candidate generation, data expansion,
  challenge-set construction, prompt hardening, LoRA/base-model policy changes,
  or public adapter/checkpoint release.

#### Scenario: Fail closed on unsafe or incomplete runtime evidence
- **WHEN** A100 connectivity, safe GPU placement, remote dependencies,
  previous-control step evidence, boundary verification, training, prediction,
  or evaluation cannot be verified safely
- **THEN** the system MUST write a single blocked artifact under
  `reports/public-sample/step-matched-canonical-slot-ablation/`
- **AND** it MUST NOT launch partial substitute experiments, fabricate metrics,
  create a design-only/review-only/candidate-only evidence phase, or recommend
  DPO or candidate expansion as the immediate next step.
