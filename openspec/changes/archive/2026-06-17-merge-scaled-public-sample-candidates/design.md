## Context

The preceding materialization phase generated `138` reviewed, public-safe
scaled public-sample candidate seeds and `414` SFT candidate rows without
mutating the formal public sample. The formal public sample remained
`102` seeds / `261` SFT rows / `881` DPO pairs.

This phase turns those reviewed candidates into a formal data boundary. It is a
data and evidence phase only.

## Decisions

1. Preserve candidate split labels.

   The scaled candidates were designed to rebalance the public sample toward a
   240-seed milestone. The merge preserves candidate `train`, `dev`, and `test`
   labels instead of forcing all candidates into train.

2. Use the existing dataset builder for derived artifacts.

   The merge only appends formalized seed rows, then delegates SFT/DPO/manifest
   generation to `build_public_sample_dataset`. This keeps DPO construction and
   public validation behavior aligned with the rest of the repository.

3. Treat the merge as a comparison-boundary change.

   Evidence and docs must warn that metrics bound to the old manifest are not
   directly comparable to metrics on the new formal sample. Any model-quality
   claim requires a later phase that explicitly binds to the new manifest.

4. Fail closed on claims.

   The report writer rejects unsupported true scope or claim fields, including
   training, prediction, A100 execution, prompt change, evaluator change, slot
   normalization, model-quality claim, checkpoint release, or adapter release.

## Validation Plan

- Focused pytest for candidate materialization and scaled merge tests.
- Full pytest.
- Ruff over `src/`, `scripts/`, and `tests/`.
- Public dataset validation.
- DPO check.
- OpenSpec strict validation.
- Leak scan over touched public docs and artifacts.
- `git diff --check`.
