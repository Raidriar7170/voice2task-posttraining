## Context

The prior A100 schema retry wrapper-boundary rerun produced useful negative evidence:

- strict `json_valid_rate=0.0` and `contract_exact_match=0.0`
- raw output as whole JSON object for `3/3` rows
- raw `task_type` missing for `3/3` rows
- retry output with visible `task_type="search"` but prose/Markdown wrapper for `3/3` rows
- `generation_trace.jsonl` recorded raw attempts only

The local instrumentation phase added `attempt=raw_attempt` and `attempt=retry_attempt` trace rows for future exports. This phase runs the same prediction-only train split on A100 to observe the real retry trace shape.

## Decision

Run one A100 prediction-only rerun using the existing private train-split adapter and current local code with:

- `prediction_split=train`
- `overfit_diagnostic=true`
- `generalization_claim=false`
- `schema_retry_enabled=true`
- `schema_repair_applied=false`
- explicit `CUDA_VISIBLE_DEVICES=<one-idle-gpu>` after `nvidia-smi` occupancy inspection

Keep all remote files created by this phase under the approved A100 project root (`<approved_a100_project_root>` in public artifacts). Do not copy raw logs, private overrides, checkpoints, adapters, caches, host details, SSH details, tokens, or private paths into git.

## Evidence Plan

- Bring back only sanitized public-safe artifacts under `reports/public-sample/a100-retry-generation-trace-rerun/`.
- Preserve predictions and decoded summaries without coercion or re-score.
- Add a retry-trace diagnosis that reports:
  - raw and retry trace row counts,
  - per-row attempt coverage,
  - retry finish states, EOS visibility, and token counts,
  - strict final metrics unchanged by the diagnostic,
  - whether retry wrapper symptoms persist.
- Validate all committed artifacts with focused tests, full test suite, OpenSpec strict validation, and leak scans.

## Risks

- The private adapter may still emit wrapper text; that is valid negative evidence and must not be reframed as a phase failure.
- If no GPU is safely idle or remote access/override state is ambiguous, stop before launching.
- If a real rerun completes but sanitized artifacts fail privacy validation, stop before committing.
