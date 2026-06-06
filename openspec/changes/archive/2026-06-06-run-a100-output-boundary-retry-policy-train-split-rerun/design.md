## Context

The current `main` includes the archived output-boundary and retry-policy repair. The shared formatter now exposes prompt constraint flags for single-root JSON object guidance, no premature root close before `normalized_command`, and public-readonly `task_type="search"` not `search_web`. The schema retry prompt now asks for exactly one minified JSON object, repeats the single-root contract shape, prohibits Markdown/prose/code fences, and repeats the `task_type="search"` guidance.

The latest A100 evidence is `reports/public-sample/a100-public-readonly-search-policy-train-split-rerun/`. It showed real private-adapter train-split output, but final strict JSON validity and exact match were both `0/3`. Raw public-readonly fields were visible in all three rows, but every row remained malformed and every retry output was rejected as a JSON fragment/prose wrapper. The local repair evidence in `reports/public-sample/public-readonly-output-boundary-retry-policy/` explicitly states that it is preparation only and does not prove model recovery.

This phase asks one narrow remote question: does the current prompt/retry policy alter those same train-row private-adapter outputs when run through the existing prediction path?

## Goals / Non-Goals

**Goals:**

- Run one explicitly authorized A100 prediction-only train-split rerun.
- Reuse the existing private train-split adapter; do not retrain or create a new adapter.
- Keep the evidence train-internal with `prediction_split=train`, `overfit_diagnostic=true`, and `generalization_claim=false`.
- Preserve private runtime boundaries: raw logs, private overrides, host details, checkpoints, adapters, caches, private paths, tokens, and SSH details stay out of git.
- Import sanitized evidence that separates prompt constraint visibility, prediction-source provenance, strict schema metrics, retry status, task type/route/safety/confirmation/slot/normalized-command observations, row-level family counts, and non-claim boundaries.
- Publish concise Chinese Human Brief and loop closeout with honest limitations.

**Non-Goals:**

- No SFT/DPO/GRPO training.
- No dev/test, full-public-sample, public full-corpus, production, release, or live-browser benchmark evaluation.
- No checkpoint release, adapter release, public model upload, deployment, PR creation, or push.
- No post-hoc slot normalization, semantic-equivalence scoring, string canonicalization of predictions, rule-baseline replacement, fixture-mode replacement, gold-contract repair, parser relaxation, or metric re-score.

## Decisions

1. **Prediction-only rerun.**
   - Rationale: the latest local change affects prediction and retry prompt serialization. Reusing the same private adapter isolates the prompt/retry variable.
   - Alternative considered: retrain with the repaired prompt. Rejected for this phase because it would mix prompt-inference effects with training effects.

2. **Train split only.**
   - Rationale: prior evidence is a train-split diagnostic. If the adapter cannot recover the same train-row contract fields under the repaired prompt/retry policy, dev/test evaluation remains premature.
   - Alternative considered: run all 12 public-sample rows. Rejected because it would blend train-internal observation with held-out/generalization claims.

3. **Keep strict whole-string JSON parsing and exact-match evaluation.**
   - Rationale: this phase observes whether model output changes. It must not hide fragment/prose failure modes by relaxing parsing or metrics.
   - Alternative considered: parse JSON fragments from retry text. Rejected because prior evidence explicitly needs invalid outputs to remain invalid.

4. **Report row-level policy evidence separately.**
   - Rationale: final `contract_exact_match` can hide whether remaining failures are schema boundary, retry wrapper, task type, route, safety reason, confirmation, slots, or normalized-command. Evidence must separately report field counts while preserving strict final metrics.

## Risks / Trade-offs

- [Risk] A100 access, idle GPU, private adapter, or dependency state is unavailable. -> Mitigation: retry transient access failures in-bounds, then stop blocked without substituting fixture evidence.
- [Risk] The rerun remains `0/3` strict valid/exact or worsens some field. -> Mitigation: report it as bounded negative evidence; do not widen to training repair inside this phase.
- [Risk] A positive train-split result is overclaimed. -> Mitigation: state explicitly that train-internal field improvement does not prove dev/test generalization, model quality, release readiness, production readiness, or live-browser improvement.
- [Risk] Private paths or logs leak into committed artifacts. -> Mitigation: import only sanitized JSON/Markdown evidence and run leak-scan over evidence, Human Briefs, loop report, and archived OpenSpec.
