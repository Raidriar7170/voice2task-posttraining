## Context

The archived A100 first-pass output-boundary rerun produced real private-adapter train-split predictions with `prediction_output_boundary` visible in both metadata and prompt snapshots. The observed output still remained `3/3` Markdown-wrapped JSON fragments, strict schema-valid output remained `0/3`, and both raw and retry attempts reached EOS rather than a max-token cutoff.

This change is a local evidence diagnosis over already committed public-safe artifacts. It does not rerun A100, train, relax parsing, or rewrite predictions.

## Goals / Non-Goals

**Goals:**

- Explain wrapper persistence using existing A100 sidecars: prediction metadata, prompt snapshot, raw decoded summary, generation trace, schema guard summary, and diagnosis.
- Distinguish boundary visibility, stop/finish-state evidence, strict parser behavior, and model output formatting behavior.
- Publish a compact diagnosis pack and Chinese Human Brief that preserve negative evidence and non-claim boundaries.

**Non-Goals:**

- No model training, A100 prediction rerun, DPO, GRPO, checkpoint release, adapter release, deployment, parser relaxation, evaluator metric change, prediction repair, prediction re-score, semantic-equivalence scoring, slot normalization, or live-browser benchmark claim.
- No new model-quality, held-out generalization, model-recovery, production-readiness, or release claim.

## Decisions

1. Diagnose from committed public-safe artifacts only.

   The source rerun is already real A100 evidence. Reusing its sanitized sidecars is enough to separate wrapper persistence from private runtime concerns without launching another private job.

2. Treat Markdown fences as model-output formatting behavior, not a parser bug.

   Strict parser behavior is intentionally preserved. The diagnosis should record that embedded JSON may be schema-like while the final output remains invalid because wrappers are outside the root JSON object.

3. Keep stop evidence separate from wrapper evidence.

   EOS-observed finish states show the generation stopped cleanly; they do not imply the decoded output obeyed the requested boundary. The diagnosis should avoid framing this as a stop-boundary failure unless evidence supports it.

4. Keep the next recommendation diagnostic, not corrective.

   If wrapper persistence remains, the next phase should be a separately scoped behavior proposal or training/data investigation, not an implicit parser relaxation or silent output repair.

## Risks / Trade-offs

- [Risk] The diagnosis over-interprets model internals from three train rows. -> Keep it as evidence-only and train-split-only.
- [Risk] Wrapper persistence is mistaken for no output-boundary visibility. -> Record prompt/metadata boundary booleans explicitly.
- [Risk] EOS-observed traces are mistaken for schema success. -> Keep strict schema-valid counts and wrapper counts in the same summary.
- [Risk] A reader wants an immediate fix. -> Recommend a bounded follow-up, but do not change behavior in this phase.
