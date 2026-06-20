## Why

The previous canonical slot paired SFT A/B used the same epoch count while
treatment had more train rows, so treatment received more optimizer updates than
control. A step-matched rerun is needed to isolate whether the reviewed
canonical slot-boundary train-only data itself improves held-out contract
quality under the same training compute budget.

## What Changes

- Add a bounded one-seed step-matched SFT A/B phase for canonical slot-boundary
  data.
- Re-verify that control and treatment share identical frozen dev/test sample
  IDs, order, input text, and gold Browser Task Contracts before training.
- Derive the unified training budget from the prior control run's actual or
  reconstructed optimizer-step budget and train fresh control/treatment adapters
  with identical `max_steps`, batch, scheduler, seed, prompt, tokenizer,
  decoding, and evaluator settings.
- Generate public-safe artifacts under
  `reports/public-sample/step-matched-canonical-slot-ablation/`, including
  boundary verification, training summaries, dev/test metrics, paired row-level
  analysis, family deltas, bootstrap diagnostics, comparison, and decision.
- Keep the result to one of the bounded decision labels:
  `PASS_STEP_MATCHED_PILOT`, `POSITIVE_BUT_INCONCLUSIVE`,
  `NO_CANONICAL_DATA_SIGNAL`, or `REGRESSION_OR_GUARDRAIL_FAILURE`.
- Stop after the one-seed phase. Do not launch multi-seed replication, DPO/GRPO,
  Contract V2 implementation, data expansion, challenge sets, or candidate
  design from this change.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `supervised-contract-tuning`: require step-matched fresh SFT training for this
  canonical slot ablation and public-safe observed training-budget metadata.
- `contract-evaluation`: require step-matched boundary verification, paired
  row-level comparison, bootstrap diagnostics, fixed pilot gate, bounded
  decision labels, and public-safe claims.

## Impact

- Adds new step-matched A100 SFT and prediction config templates.
- Adds report/evaluation helpers for boundary verification, training-budget
  evidence, row/family paired deltas, bootstrap diagnostics, and decision output.
- Adds focused tests for step-matched config invariants and public artifact
  shape.
- Adds OpenSpec artifacts and a concise Chinese Human Brief for the phase.
- Does not change public sample data, train/dev/test splits, evaluator
  semantics, prompt hardening, LoRA tuning policy, base model family, or public
  release posture.
