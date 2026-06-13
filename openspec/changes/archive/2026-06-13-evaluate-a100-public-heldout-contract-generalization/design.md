## Context

The archived `repair-extract-price-canonical-wording` phase produced a private A100 7B adapter that reached `contract_exact_match=1.0` on the public train split. Its own manifest explicitly labels that result as `prediction_split=train`, `overfit_diagnostic=true`, and `generalization_claim=false`.

The next evidence gap is whether the same adapter emits strict Browser Task Contracts on held-out public sample rows. The committed manifest already has `split_counts` for `train`, `dev`, and `test`, so this phase can reuse the public dataset without generating new seed data or changing training behavior.

## Goals / Non-Goals

**Goals:**

- Evaluate the existing private 7B adapter on public `dev` and `test` rows.
- Preserve split separation in predictions, metrics, diagnostics, and final interpretation.
- Keep evidence public-safe and sanitized, with private adapter/base-model paths represented only as placeholders.
- Record whether held-out strict contract behavior is stable, partial, or failed.

**Non-Goals:**

- Do not run SFT or DPO training.
- Do not edit prompt policy, dataset generation, DPO hard negatives, or evaluator semantics.
- Do not treat public held-out success as private-corpus or production generalization.
- Do not copy checkpoints, adapters, raw logs, caches, private overrides, host details, SSH details, tokens, or private corpus rows into git.

## Decisions

1. Run `dev` and `test` as separate prediction jobs.

   Separate jobs keep split metrics auditable. A combined manifest may summarize both, but each split keeps its own predictions, sidecars, schema/alignment diagnostics, and metrics.

2. Reuse the canonical wording adapter without retraining.

   This phase answers a diagnostic question about the already-produced adapter. Any behavior-changing fix belongs in a later OpenSpec phase if held-out predictions expose residuals.

3. Treat public held-out evidence as stronger than train-split evidence, but still bounded.

   Public `dev`/`test` rows help detect memorization of the public train rows. They still do not prove private-corpus behavior, live browser performance, production readiness, or release quality.

## Risks / Trade-offs

- Public held-out rows are still small and synthetic -> Mitigation: report exact row counts and avoid broad generalization language.
- One split could pass and the other fail -> Mitigation: publish split-specific metrics and a combined interpretation that does not hide split failures.
- Remote adapter path may be missing or stale -> Mitigation: verify the private adapter exists on A100 before launching prediction; stop if unavailable.
- A100 GPU availability may be unsafe -> Mitigation: inspect `nvidia-smi`, select an idle GPU explicitly, and stop if placement is unclear.
