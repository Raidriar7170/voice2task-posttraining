## Why

The targeted 7B family coverage probe moved dev/test strict exact from zero to `1/6`, but the remaining failures are now value residuals rather than schema, task, route, safety, or confirmation failures. The archived residual diagnosis recommends `design_slot_value_generalization_cases_before_broad_scaling_or_dpo`.

Before changing the public sample, broadening training, or running DPO, we need a public-safe case design artifact that maps each residual bucket to minimal candidate train/validation examples. This keeps the next data decision reviewable and prevents accidental held-out leakage.

## What Changes

- Add a local case-design diagnostic that reads the archived targeted residual diagnosis.
- Generate candidate case specifications for:
  - `slot_value_language_variant`
  - `slot_value_canonical_phrase_drift`
  - `normalized_command_paraphrase_drift`
- Produce a public-safe report under `reports/public-sample/slot-value-generalization-case-design/`.
- Generate a concise Chinese Human Brief with project-stage progress and non-claim boundaries.

## Non-Goals

- Do not edit `data/public-samples/seed_traces.jsonl`.
- Do not rebuild the public sample dataset.
- Do not generate new training rows.
- Do not run A100 training or prediction.
- Do not run DPO/GRPO.
- Do not change evaluator semantics, exact-match scoring, or slot normalization.
- Do not claim model recovery, held-out recovery, private-corpus generalization, production readiness, adapter release, or checkpoint release.

## Impact

- `src/voice2task/evaluation.py`: add a deterministic case-design function over residual diagnosis evidence.
- `src/voice2task/reports.py`: add a public-safe report writer and manifest.
- `src/voice2task/cli/eval.py`: add a local CLI command.
- `tests/`: add focused tests for case coverage, CLI output, committed evidence, and boundaries.
- `reports/public-sample/`: add the case-design evidence pack.
- `docs/human-briefs/`: add the phase brief.
