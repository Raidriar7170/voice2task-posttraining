## ADDED Requirements

### Requirement: Run canonical slot-boundary paired SFT ablation
The system SHALL support a bounded paired SFT ablation that trains fresh control
and treatment LoRA adapters to test whether canonical slot-boundary train-only
data improves held-out contract quality.

#### Scenario: Train fresh paired adapters
- **WHEN** the ablation is authorized, the comparison boundary verification has
  passed, A100 execution is reachable, and an idle GPU can be selected safely
- **THEN** the system MUST train a fresh control adapter on the
  `public-sample-20260617T152259Z` train SFT rows and a fresh treatment adapter
  on the `public-sample-20260619T090925Z` train SFT rows
- **AND** it MUST NOT reuse an older adapter as the paired control

#### Scenario: Keep paired training settings identical
- **WHEN** the control and treatment adapters are trained
- **THEN** both arms MUST use `Qwen/Qwen2.5-7B-Instruct`, the same LoRA rank,
  alpha, dropout, learning rate, epochs or max steps, batch size, gradient
  accumulation, random seed, prompt template, tokenizer, decoding parameters,
  evaluator, and frozen dev/test inputs
- **AND** the committed metadata MUST record these paired invariants without
  exposing private A100 paths, hosts, SSH details, checkpoints, adapters, raw
  logs, caches, tokens, or secrets

#### Scenario: Restrict ablation to SFT
- **WHEN** the ablation runs for the treatment manifest
- **THEN** the system MUST train only on SFT rows and MUST NOT run DPO, GRPO, an
  LLM judge, prediction repair, semantic-equivalence scoring, or evaluator
  relaxation

#### Scenario: Fail closed on unsafe runtime
- **WHEN** A100 connectivity, safe GPU placement, remote dependencies, or the
  paired training command cannot be verified safely
- **THEN** the system MUST write blocked evidence for
  `reports/public-sample/canonical-slot-paired-sft-ablation/` and MUST NOT
  launch partial training, fabricate metrics, or create a replacement
  design-only, review-only, or candidate-only phase
