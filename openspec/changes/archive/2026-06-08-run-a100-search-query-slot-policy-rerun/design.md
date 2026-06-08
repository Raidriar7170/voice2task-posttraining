# Design

## Context

Current committed public sample search rows now use compact search query targets:

```json
{"slots":{"query":"北京明天天气"},"normalized_command":"搜索北京明天天气"}
```

The prior A100 retry-template rerun used the older spaced gold rows in its copied `train_split_gold.jsonl`. Its predictions already showed:

- row 1: schema-valid via retry, but `slots.city/date` and normalized-command mismatch,
- row 2: schema-valid raw, but `slots.city/date`,
- row 3: schema-valid via retry and compact `slots.query`.

This phase reruns prediction with the current prompt and current public sample manifest. It must produce fresh evidence rather than retroactively editing or re-scoring the old rerun.

## Execution Boundary

- Use the existing private adapter and a repo-external private prediction override on A100.
- Use `prediction_split=train`, `overfit_diagnostic=true`, `generalization_claim=false`, `schema_retry_enabled=true`, greedy decoding, and explicit `CUDA_VISIBLE_DEVICES`.
- Inspect `nvidia-smi` before launch and select an idle GPU only when safe.
- Keep all remote raw logs, private configs, caches, checkpoints, adapters, and private paths out of git.

## Evidence Shape

Sanitized public evidence should include:

- `predictions.jsonl`
- `prediction_metadata.json`
- `prompt_snapshot.json`
- `raw_decoded_summary.jsonl`
- `generation_trace.jsonl`
- `train_split_gold.jsonl`
- `metrics.json` and `metrics.md`
- `schema_guard_summary.json` and `.md`
- `slot_policy_rerun_diagnosis.json` and `.md`
- `manifest.json`
- leak scan sidecars

The diagnosis should explicitly report compact-query target checks, row-level slot/exact-match outcome, and whether the observed result is a train-internal rerun only.

## Alternatives Considered

- Re-score the previous A100 rerun against the new compact gold target.
  - Rejected because it would reinterpret historical evidence and blur whether current prompt/runtime changed behavior.
- Run training before prediction.
  - Rejected because the next question is narrower: whether current target/prompt policy changes prediction-only evidence for the existing adapter.
- Accept `city/date` as equivalent to `query`.
  - Rejected because the evaluator remains strict and this phase must not add slot normalization.

## Risks And Mitigations

- Risk: The result may still be `0/3` or only partially improve.
  - Mitigation: report exact row-level outcome without model-quality or generalization claims.
- Risk: A100 GPUs are busy or private adapter paths are unavailable.
  - Mitigation: stop as blocked rather than using an unsafe GPU or writing outside approved directories.
- Risk: Sanitized artifacts accidentally expose private paths.
  - Mitigation: run leak scans before commit and keep private overrides/logs outside git.
