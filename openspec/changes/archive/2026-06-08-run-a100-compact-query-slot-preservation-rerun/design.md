## Context

The previous A100 first-pass fence-suppression rerun reached `3/3` strict schema-valid train predictions, but exact match remained `2/3` because `seed-search-weather-aug-1` emitted decomposed `slots={"city":"北京","date":"明天","topic":""}` instead of compact `slots={"query":"北京明天天气"}`. The just-archived compact query slot preservation phase added a public DPO `decomposed_search_slots` hard negative and strengthened prompt/data evidence locally without running A100. This phase is the narrow follow-up: run one train-split prediction-only A100 rerun to observe whether the current private adapter path emits the compact query slot shape.

## Goals / Non-Goals

**Goals:**

- Run one authorized A100 prediction-only train-split rerun against the current public-sample train rows and current compact query slot preservation prompt/data policy.
- Keep private overrides, raw logs, model caches, checkpoints, adapters, and host details outside git.
- Publish sanitized public evidence that records strict metrics, row-level slot shape outcomes, prompt/policy metadata, source residual comparison, validation commands, leak scans, and explicit non-claims.
- Generate a concise Chinese Human Brief for the phase.

**Non-Goals:**

- No SFT/DPO training, hyperparameter tuning, adapter/checkpoint release, public full-corpus release, evaluator relaxation, parser relaxation, slot normalization, semantic-equivalence scoring, prediction repair, prediction replacement, re-score, production-readiness claim, held-out generalization claim, live-browser benchmark claim, broad model-quality claim, generic chat fine-tuning, skill routing, GUI action policy learning, or first-phase GRPO.

## Decisions

1. Reuse the existing trained-adapter prediction export path.

   The repository already supports public-safe A100 train-split prediction exports with prompt snapshots, sanitized raw decoded summaries, generation traces, schema guard summaries, metrics, and leak scans. This phase should not invent a new runner; it should use the existing `voice2task.cli.train sft-predict` path with a repo-external private override.

2. Treat the rerun as train-internal diagnostic evidence only.

   The rerun uses public-sample train rows to test a known residual. Even if strict exact match improves to `3/3`, the result is not held-out generalization, production readiness, live-browser benchmark evidence, checkpoint release, or model-quality proof.

3. Preserve strict evaluator semantics.

   The success question is whether the prediction itself uses compact `slots.query`. The evaluator must not normalize `city/date/topic` into `query`, repair predictions, or re-score historical outputs.

4. Fail closed on A100 safety or privacy uncertainty.

   Before GPU work, inspect GPU/process occupancy, choose a safe idle GPU explicitly with `CUDA_VISIBLE_DEVICES`, and keep all new remote files under the approved private project root. If access, overrides, GPU safety, or private/public artifact separation is unclear, stop blocked rather than fabricating fixture evidence.

## Risks / Trade-offs

- [Risk] No A100 GPU is safely idle or process ownership is unclear. -> Mitigation: stop and record blocked status; do not interrupt other users or launch speculative work.
- [Risk] Private override or adapter path is unavailable. -> Mitigation: stop blocked with a public-safe reason; do not commit private paths or host details.
- [Risk] Rerun still emits decomposed slots or regresses wrapper/schema behavior. -> Mitigation: preserve sanitized failure evidence and report strict metrics honestly.
- [Risk] Improved train split result is overstated. -> Mitigation: evidence, Human Brief, and tests must explicitly bound claims and state that dev/test validation remains future work.
