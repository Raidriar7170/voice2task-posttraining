# run-a100-search-query-slot-policy-rerun

## Why

The retry-template A100 rerun recovered schema-valid output on the bounded train split, but strict exact match stayed at `0/3`. The follow-up local policy phase aligned the public search/weather gold targets and prompts to compact `slots.query` (`北京明天天气`) instead of the older spaced target (`北京 明天 天气`).

The next bounded check is a prediction-only A100 rerun using the current compact search query target policy. This phase should answer only whether the existing private adapter, current prompt, and current train-split targets improve the strict row-level slot/exact-match result.

## What Changes

- Run one authorized A100 prediction-only train-split rerun with the existing private adapter, current code, current public sample manifest, and a repo-external private override.
- Preserve strict parser/evaluator semantics: no slot normalization, semantic equivalence, prediction repair, prediction replacement, parser relaxation, metric relaxation, or re-score.
- Publish only sanitized public evidence under `reports/public-sample/a100-search-query-slot-policy-rerun/`.
- Compare the new rerun against:
  - `reports/public-sample/a100-retry-template-boundary-rerun/`
  - `reports/public-sample/retry-template-slot-exact-match-mismatch-diagnosis/`
  - `reports/public-sample/search-query-slot-target-policy/`
- Generate a Chinese Human Brief at `docs/human-briefs/2026-06-08-run-a100-search-query-slot-policy-rerun.html`.

## Non-Goals

- No training, fine-tuning, DPO, GRPO, checkpoint release, adapter release, public full-corpus release, production-readiness claim, held-out generalization claim, model-quality claim, or live-browser benchmark claim.
- No committed private override, raw remote log, private path, SSH detail, host detail, token, secret, checkpoint, adapter, cache, or private corpus row.
- No dev/test rerun and no public metric reinterpretation of older predictions.

## Impact

- Affected execution: A100 prediction-only rerun, train split only, current compact search query target policy.
- Affected artifacts: sanitized rerun evidence, Human Brief, archived OpenSpec artifacts, and validation sidecars.
- Affected specs: `supervised-contract-tuning`, `contract-evaluation`, and `voice2task-dataset-preparation`.
