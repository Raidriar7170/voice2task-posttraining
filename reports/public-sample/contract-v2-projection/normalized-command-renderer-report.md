# Normalized Command Renderer Report

Status: blocked before renderer evaluation.

The renderer prototype was not executed because the latest committed
step-matched evidence root lacks raw Control/Treatment dev/test prediction
contracts and dev/test gold JSONL contracts.

The bounded renderer policy for a future rerun remains:

- use only `task_type`, `route`, and slots from V2 Core;
- do not read original or predicted `normalized_command`;
- do not call an LLM judge;
- do not infer semantic equivalence;
- do not alter or merge slots;
- return `unsupported` with a reason when a task/route/slot pattern cannot be
  rendered deterministically.

Renderer coverage metrics are unavailable for this blocked run.
