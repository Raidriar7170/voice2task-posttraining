## Context

The current main branch includes the local confirmation-required prompt repair: `SYSTEM_PROMPT` now states that `confirmation_required` is a required boolean top-level field, and the low-risk weather/search example includes `confirmation_required=false`. The latest remote baseline is `reports/public-sample/a100-route-ontology-train-split-rerun/`: it reached the route ontology prompt path and produced raw `route=search_web` for all three train rows, but all final predictions stayed schema-invalid because raw attempts omitted `confirmation_required` and retry attempts were Markdown/prose-wrapped fragments rejected by the strict parser.

This phase asks one narrow remote question: does the confirmation-required prompt repair alter those same train-row private-adapter outputs when run through the existing prediction path?

## Goals / Non-Goals

**Goals:**

- Run one explicitly authorized A100 prediction-only train-split rerun.
- Reuse the existing private train-split adapter; do not retrain or create a new adapter.
- Keep the evidence train-internal with `prediction_split=train`, `overfit_diagnostic=true`, and `generalization_claim=false`.
- Preserve private runtime boundaries: raw logs, private overrides, host details, checkpoints, adapters, caches, private paths, tokens, and SSH details stay out of git.
- Import sanitized evidence that separates raw attempt schema validity, retry attempt schema validity, validated output source, `confirmation_required` presence, parse statuses, prompt constraints, and final contract metrics.
- Publish concise Chinese Human Brief and loop report with non-overclaim boundaries.

**Non-Goals:**

- No SFT/DPO/GRPO training.
- No dev/test, full-public-sample, public full-corpus, production, release, or live-browser benchmark evaluation.
- No checkpoint release, adapter release, public model upload, deployment, PR creation, or push.
- No post-hoc `confirmation_required` defaulting in prediction artifacts, schema coercion, rule-baseline replacement, fixture-mode replacement, or gold-contract repair.

## Decisions

1. **Prediction-only rerun.**
   - Rationale: the latest local change affects prompt serialization and prompt constraint metadata at prediction time. Reusing the same private adapter isolates the confirmation-required prompt variable.
   - Alternative considered: retrain with the new prompt. Rejected for this phase because it would mix prompt-inference effects with training effects.

2. **Train split only.**
   - Rationale: prior evidence is a train-split diagnostic. If the adapter cannot improve train-row contract completeness under the repaired prompt, dev/test evaluation remains premature.
   - Alternative considered: run all 12 public-sample rows. Rejected because it would blend train-internal recovery with held-out generalization.

3. **Keep strict parser and schema guard.**
   - Rationale: accepting Markdown/prose fragments or filling `confirmation_required` would hide the exact failure this phase is meant to measure.
   - Alternative considered: post-process missing `confirmation_required=false`. Rejected because it is output coercion and would overstate model correctness.

4. **Report confirmation-required evidence separately.**
   - Rationale: final `json_valid_rate` alone can obscure whether the specific missing-field symptom changed. Evidence must separately report missing `confirmation_required`, raw/retry/validated source, and prompt constraints.
   - Alternative considered: summarize only pass/fail. Rejected because prior failures were contract-like but still schema-invalid.

## Risks / Trade-offs

- [Risk] A100 access, idle GPU, private adapter, or dependency state is unavailable. -> Mitigation: retry transient access failures in-bounds, then stop blocked without substituting fixture evidence.
- [Risk] The rerun remains `0/3` schema-valid. -> Mitigation: report it as bounded negative evidence; do not widen to training repair inside this phase.
- [Risk] Private paths or logs leak into committed artifacts. -> Mitigation: import only sanitized JSON/Markdown evidence and run leak-scan over evidence, Human Briefs, loop report, and archived OpenSpec.
- [Risk] A positive train-split result is overclaimed. -> Mitigation: state explicitly that train-internal recovery does not prove dev/test generalization, release readiness, production readiness, or live-browser improvement.
