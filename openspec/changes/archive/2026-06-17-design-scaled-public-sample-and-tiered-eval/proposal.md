## Why

The latest current-manifest A100 SFT retry shows stable schema output and recovered safety recall, but strict full-contract exact remains low on formal held-out dev/test. Narrow repair cycles now produce trade-offs rather than strict recovery, so the next step should design a larger, better-balanced public-sample expansion and diagnostic tiered evaluation plan before mutating data or launching another training run.

## What Changes

- Publish a bounded design-only plan for scaling the formal public sample from 102 seeds toward a larger target set, with explicit family balance, augmentation policy, and accepted/rejected target coverage.
- Define a tiered evaluation design that decomposes strict failure into structural, route/task, safety/confirmation, slot, and exact-contract layers while preserving strict `contract_exact_match` and strict `slot_f1` as public headline metrics.
- Produce public-safe planning artifacts and a Human Brief that explain why broad data/eval design is now preferred over another immediate narrow SFT retry.
- Do not materialize new seed rows, regenerate SFT/DPO rows, run SFT/DPO/GRPO, change prompts, relax evaluator metrics, repair predictions, publish checkpoints/adapters, or claim model recovery.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `voice2task-dataset-preparation`: Add requirements for a design-only scaled public-sample plan before any larger seed materialization.
- `contract-evaluation`: Add requirements for a tiered evaluation design that remains diagnostic and does not replace strict metrics.

## Impact

- Affected public evidence: a new planning report under `reports/public-sample/` and a concise Human Brief under `docs/human-briefs/`.
- Affected specs: `voice2task-dataset-preparation` and `contract-evaluation`.
- No public sample files, model configs, training scripts, evaluator semantics, checkpoints, adapters, private corpora, or remote A100 runtime outputs are changed by this design phase.
