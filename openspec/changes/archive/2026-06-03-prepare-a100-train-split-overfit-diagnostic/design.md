## Context

The latest diagnostics show that the committed public targets are valid Browser Task Contracts, while post-recovery private-adapter predictions still fail schema validation with path-like routes and list-shaped slots. Three read-only reviews converged on a narrower next step: do not immediately rerun A100. First prepare a train-split overfit diagnostic path that captures objective, prompt, decoding, and row-level evidence.

The current SFT path pre-renders the full chat into a single `text` field for `SFTTrainer`. That may optimize system/user/template tokens as well as assistant JSON tokens, so loss improvement alone cannot prove the model learned the contract target. The old A100 prediction artifacts also lack prompt snapshots, generated token counts, EOS/finish state, and sanitized raw decoded summaries, so truncation and prompt mismatch remain evidence gaps.

## Goals / Non-Goals

**Goals:**

- Prepare a bounded A100 train-split overfit diagnostic workflow without launching remote training from this local phase.
- Add public-safe prediction sidecars for prompt snapshot, sanitized raw decoded summary, generation trace, and train-split metadata.
- Add an objective inspection surface that records prompt-mask / assistant-loss status only when real label evidence is available, and otherwise reports an unavailable state before overfit evidence is interpreted.
- Add config/report surfaces for `prediction_split=train` and `overfit_diagnostic=true`.
- Keep invalid model outputs visible as failures; do not repair, normalize, coerce, or replace predictions.

**Non-Goals:**

- No direct A100 execution in this local preparation phase.
- No checkpoint or adapter release.
- No production-readiness, full-private-corpus, live-browser benchmark, or generalization claim.
- No generic chat fine-tuning, skill routing, GUI action policy learning, or first-phase GRPO.
- No public commit of private overrides, raw logs, checkpoints, adapters, caches, private paths, host details, SSH details, tokens, or private corpus rows.

## Decisions

1. **Prepare evidence sidecars before rerunning A100.**
   - Rationale: the previous rerun lacked raw decoded/token/EOS evidence, making several root-cause hypotheses unverifiable.
   - Alternative considered: rerun immediately with the current artifact set. That would risk another failure report with the same evidence gaps.

2. **Treat train-split overfit as a diagnostic, not a quality benchmark.**
   - Rationale: the committed train split has three `search/search_web` rows. Passing it would show train-internal recovery, not held-out generalization.
   - Alternative considered: combine train and all-split evaluation into one success claim. That would blur overfit sanity checks with product metrics.

3. **Add fail-closed objective inspection before changing the training stack.**
   - Rationale: TRL version behavior differs across the historical A100 stack and local lockfile. A local inspection artifact can expose whether objective evidence is unavailable before a larger migration, without implying assistant-only loss has been proven.
   - Alternative considered: immediately rewrite SFT training to modern `SFTConfig`. That may be correct later, but it is a larger training-stack change than this preparation phase needs.

4. **Use sanitized summaries instead of full raw decoded logs.**
   - Rationale: decoded text may contain private paths or accidental logs. A bounded prefix/suffix/parse-status summary plus leak scan keeps public evidence useful and safer.

## Risks / Trade-offs

- [Risk] Sidecar summaries may omit a clue present in full raw decoded text -> Mitigation: record bounded prefix/suffix, parse status, generated token count, and finish state while keeping raw logs private.
- [Risk] Objective inspection may be unavailable without train dependencies -> Mitigation: report dependency availability and fail closed rather than implying assistant-only loss is active.
- [Risk] A train-split overfit pass may be overclaimed -> Mitigation: manifest/report MUST set `generalization_claim=false` and label the result train-internal only.
- [Risk] Private A100 override details may leak -> Mitigation: committed configs remain placeholders and all copied artifacts must pass leak scan.

## Open Questions

- Which TRL route should become the durable training implementation: pinned legacy stack with `DataCollatorForCompletionOnlyLM`, or modern `SFTConfig` with completion/assistant-only loss?
- Should a later phase add a balanced public/private-small corpus after the train-split diagnostic is interpretable?
