## Context

The previous A100 output-boundary retry-policy rerun produced:

- strict `json_valid_rate=0.0` and `contract_exact_match=0.0`
- raw output as whole JSON object for `3/3` rows
- raw `task_type` missing for `3/3` rows
- retry output with visible `task_type="search"` for `3/3` rows, but still prose/Markdown-wrapped and rejected

The local retry-wrapper repair added explicit no-prefix/no-suffix/no-`Here is`/no-second-object instructions. This phase checks only whether that prompt is present in the A100 prediction path and records the observed output shape.

## Decision

Use the existing private A100 adapter path and run `voice2task-train sft-predict` in prediction-only mode on the public train split with:

- `prediction_split=train`
- `overfit_diagnostic=true`
- `generalization_claim=false`
- `schema_retry_enabled=true`
- `schema_repair_applied=false`
- explicit single-GPU placement after `nvidia-smi` occupancy inspection

Do not pull private configs, raw logs, checkpoints, adapters, caches, host details, or private paths into git.

## Risks

- The model may still wrap retry output; that remains valid negative evidence, not a failure of the phase.
- If all GPUs are occupied or safe placement is unclear, stop before launching.
- If the private override cannot be created without exposing private paths, stop before launch.
