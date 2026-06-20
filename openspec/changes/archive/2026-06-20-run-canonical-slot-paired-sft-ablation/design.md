## Context

The current formal public sample is `public-sample-20260619T090925Z` after the
canonical slot-boundary formal merge. Relative to
`public-sample-20260617T152259Z`, it adds seven train-only canonical seeds,
twenty-one SFT rows, and fifty-four DPO pairs. The latest observed model
metrics target the older `public-sample-20260617T152259Z` boundary, while the
current canonical-boundary prediction baseline is blocked without metrics.

This phase is therefore not another candidate, design, review, or
prediction-only evidence phase. It is a one-seed paired SFT ablation that asks
whether the canonical train rows improve strict held-out behavior when compared
against a newly trained control adapter.

## Goals / Non-Goals

**Goals:**

- Verify that control and treatment dev/test gold rows are byte-for-byte
  comparable before causal interpretation.
- Train two fresh SFT adapters from the same base model and hyperparameter
  boundary.
- Evaluate both adapters on the same frozen dev/test inputs and report strict
  primary metrics, guardrail metrics, absolute deltas, family-level deltas, and
  recoveries/regressions.
- Produce public-safe observed-or-blocked artifacts under
  `reports/public-sample/canonical-slot-paired-sft-ablation/`.
- Apply the one-seed pilot gate before recommending any later three-seed
  confirmation.

**Non-Goals:**

- No DPO, GRPO, LLM judge, evaluator change, prediction repair, semantic
  equivalence scoring, slot normalization re-score, or deterministic
  postprocessor implementation.
- No public adapter/checkpoint release and no production-readiness,
  safety-readiness, live-browser benchmark, or held-out recovery claim unless
  the strict metrics genuinely support the bounded claim.
- No new design-only, review-only, or candidate-only evidence phase.
- No additional canonical candidate materialization if the pilot gate fails.

## Decisions

1. **Boundary verification is a hard precondition.**
   The phase first computes content hashes for each manifest's dev/test gold
   files and checks row ids, order, and gold contracts. Equal split counts are
   insufficient. If the boundary differs, the phase stops and writes blocked
   evidence recommending a shared frozen held-out set.

2. **The control adapter is freshly trained.**
   The old adapter lineage is not a paired control because it was trained under
   a different data/runtime boundary. Both arms must start from
   `Qwen/Qwen2.5-7B-Instruct` and share LoRA rank, alpha, dropout, learning
   rate, epochs or max steps, batch size, gradient accumulation, random seed,
   prompt template, tokenizer, decoding parameters, evaluator, and dev/test
   inputs.

3. **Only train data differs between arms.**
   Control uses the `public-sample-20260617T152259Z` train SFT rows
   (`261`). Treatment uses the `public-sample-20260619T090925Z` train SFT rows
   (`282`). DPO rows are recorded as out of scope even though the treatment
   manifest contains new DPO pairs.

4. **Reports are public-safe summaries of private runtime.**
   Raw A100 checkpoints, adapters, caches, private overrides, logs, host
   details, SSH details, private paths, secrets, and tokens remain outside git.
   Committed artifacts use public-safe placeholders and aggregate metrics.

5. **Pilot gate decides the next recommendation.**
   The one-seed treatment must improve dev and test `slot_value_exact_f1` by at
   least `0.03`, improve dev and test `executable_contract_pass_rate` by at
   least `0.02`, avoid `safety_recall` drops, avoid
   `unsafe_false_negative` increases, and keep confirmation accuracy decline at
   or below `0.01`. Otherwise the recommended next phase is
   `design-and-implement-contract-v2`.

## Risks / Trade-offs

- [Risk] The two manifests may not share an identical dev/test boundary even
  though counts match. -> Mitigation: stop before training and write a blocked
  boundary report.
- [Risk] A single seed can be noisy. -> Mitigation: treat the result as a pilot
  gate only; recommend three-seed confirmation only if the gate passes.
- [Risk] A100 connectivity or safe GPU placement may be unavailable. ->
  Mitigation: write one blocked artifact and stop without creating replacement
  review/design phases.
- [Risk] Public artifacts could overstate model recovery. -> Mitigation:
  reports must distinguish observed strict metrics from interpretation and
  must keep adapter/checkpoint release status private/unreleased.
