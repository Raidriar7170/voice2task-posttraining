## Why

The canonical slot-boundary formal merge advanced the current public sample to
`public-sample-20260619T090925Z`, but the latest model evidence is historical
or blocked and does not prove whether those train-only canonical rows improve
held-out contract quality. This phase runs a paired SFT ablation so the effect
of the canonical slot-boundary data is tested against a freshly trained control
rather than inferred from an old adapter.

## What Changes

- Verify the comparison boundary between control manifest
  `public-sample-20260617T152259Z` and treatment manifest
  `public-sample-20260619T090925Z` by hashing dev/test gold content, row order,
  and gold contracts before any causal training interpretation.
- Train two fresh `Qwen/Qwen2.5-7B-Instruct` LoRA SFT adapters with identical
  base model, LoRA hyperparameters, optimizer settings, seed, prompt template,
  tokenizer, decoding policy, evaluator, and frozen dev/test inputs.
- Use only SFT for this ablation: control trains on 261 train SFT rows from
  `public-sample-20260617T152259Z`; treatment trains on 282 train SFT rows from
  `public-sample-20260619T090925Z`.
- Evaluate both adapters on the same frozen dev/test boundary and publish
  public-safe control, treatment, comparison, and boundary-verification
  artifacts.
- Apply a fixed one-seed pilot gate before recommending any later three-seed
  confirmation.
- Fail closed with a single blocked artifact if the comparison boundary is not
  identical or A100 execution cannot be reached safely.
- No DPO/GRPO, evaluator change, LLM judge, prediction repair, semantic
  equivalence scoring, public adapter/checkpoint release, production-readiness
  claim, or additional candidate-design loop is part of this phase.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `supervised-contract-tuning`: add a paired canonical slot-boundary SFT
  ablation requirement that trains fresh control and treatment adapters under
  identical runtime settings.
- `contract-evaluation`: add a frozen-heldout boundary verification,
  comparison report, strict metric delta, recovery/regression, safety
  guardrail, and pilot-gate requirement for the paired SFT ablation.

## Impact

- Affected reports:
  `reports/public-sample/canonical-slot-paired-sft-ablation/control/`,
  `reports/public-sample/canonical-slot-paired-sft-ablation/treatment/`,
  `reports/public-sample/canonical-slot-paired-sft-ablation/comparison.md`,
  `reports/public-sample/canonical-slot-paired-sft-ablation/comparison.json`,
  and
  `reports/public-sample/canonical-slot-paired-sft-ablation/boundary-verification.json`.
- Affected OpenSpec artifacts: this change's proposal, design, specs, and tasks.
- Affected runtime: private A100 training and prediction only, with all raw
  checkpoints, adapters, logs, caches, private overrides, host details, SSH
  details, and private paths kept out of committed artifacts.
- Affected documentation: `CONTEXT.md`, `reports/final_status.md`, and a concise
  Chinese Human Brief after observed-or-blocked evidence exists.
