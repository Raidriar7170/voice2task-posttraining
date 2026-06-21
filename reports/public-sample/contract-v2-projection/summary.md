# Contract V2 Projection Summary

The phase is blocked before projection metrics. The current committed
step-matched evidence root is sufficient to describe the latest ablation result
as mixed / inconclusive, but insufficient to run deterministic Contract V2
projection.

## What Was Confirmed

- Latest current source root:
  `reports/public-sample/step-matched-canonical-slot-ablation/`
- Current step-matched aggregate evidence exists.
- V1 schema/evaluator source files are committed under `src/voice2task/`.
- No A100, SSH, adapter, training, DPO, or prediction generation is needed for
  projection.
- Older non-step-matched raw predictions exist but are not valid current inputs.

## What Is Missing

- Current Control dev/test raw prediction contracts.
- Current Treatment dev/test raw prediction contracts.
- Current dev/test gold contract JSONL files aligned with those predictions.

## Outcome

Decision label: `PROJECTION_BLOCKED_OR_INVALID`.

No V2 exact, executable, renderer coverage, failure contribution, family delta,
or bootstrap metrics were computed.

## Next Action

Recover or commit public-safe raw step-matched prediction and gold artifacts,
then rerun this same bounded projection evaluation. Do not use older
non-step-matched predictions as a substitute.
