## Why

The targeted 7B family coverage probe proved learnability on train and moved dev/test strict exact from zero, but strict held-out recovery is still blocked by residual value mismatches. The remaining dev/test failures are no longer schema, JSON, task type, route, safety, or confirmation failures. They are strict `normalized_command` and `slots` value mismatches.

Before broad data scaling or DPO, we need a bounded diagnosis that names the residual families, classifies the value drift, and recommends the smallest next data/generalization action without changing evaluator semantics.

## What Changes

- Add a public-safe targeted residual diagnosis for the committed A100 targeted family coverage evidence.
- Classify residuals by field, split, family, and value-drift bucket such as command paraphrase drift, slot language variant, and slot canonical phrase drift.
- Generate a committed evidence pack under `reports/public-sample/targeted-slot-value-residual-diagnosis/`.
- Add a concise Chinese Human Brief for the diagnosis.
- Keep strict `contract_exact_match` primary and keep soft slot F1 diagnostic-only.

## Non-Goals

- No new training run.
- No new data generation.
- No DPO/GRPO run.
- No prediction repair or replacement.
- No evaluator relaxation or semantic-equivalence promotion.
- No adapter/checkpoint release, production-readiness claim, or private-corpus generalization claim.

## Impact

- `src/voice2task/evaluation.py`: add diagnosis logic over public-safe targeted probe gold/predictions/alignment artifacts.
- `src/voice2task/reports.py`: add a compact public-safe residual diagnosis report writer.
- `src/voice2task/cli/eval.py`: expose the diagnosis as a local CLI.
- `tests/`: add focused tests for taxonomy, CLI output, committed evidence, and non-claim boundaries.
- `reports/public-sample/`: add the public-safe residual diagnosis evidence pack.
- `docs/human-briefs/`: add a concise Chinese companion brief.
