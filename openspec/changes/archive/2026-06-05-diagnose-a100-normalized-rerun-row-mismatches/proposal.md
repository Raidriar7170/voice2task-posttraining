# diagnose-a100-normalized-rerun-row-mismatches

## Why

The archived A100 normalized-command policy train-split rerun shows `normalized_command` exact-string matches at `2/3`, while strict final contract metrics remain unrecovered: `json_valid_rate=1/3`, `contract_exact_match=0.0`, `task_type_accuracy=0.0`, `route_accuracy=0.0`, `confirmation_accuracy=1/3`, and `slot_f1=0.0`. The remaining failures need a row-level, public-safe diagnosis that separates schema failures from schema-valid task/route/safety/slot mismatches.

## What Changes

- Publish a local evidence-only row-level mismatch diagnosis derived from the existing public-safe A100 normalized-command rerun artifacts.
- Classify each train-row failure into narrow primary families:
  - missing `confirmation_required` schema failure,
  - invalid `task_type` enum schema failure,
  - schema-valid task/route/safety/slot mismatch.
- Preserve the strict source metrics and schema guard counts without repair, normalization, re-score, semantic-equivalence labeling, prediction rerun, training rerun, prompt change, decoding change, or evaluator change.
- Add focused tests, leak-scan results, and a concise Chinese Human Brief.

## Non-Goals

- No A100 execution.
- No training, fine-tuning, decoding, prompt, retry, schema, parser, evaluator, or metric logic change.
- No semantic-equivalence scoring or normalized-command normalization.
- No prediction repair, replacement, or re-score.
- No held-out generalization, benchmark, model-quality improvement, production-readiness, checkpoint-release, adapter-release, or public full-corpus claim.

## Impact

- Affected spec: `contract-evaluation`
- Affected code: row-level evaluation/report helpers and focused tests only.
- Affected evidence: a new public-safe directory under `reports/public-sample/a100-normalized-rerun-row-mismatch-diagnosis/`.
