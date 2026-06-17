## Why

The current-train-split SFT retry readiness phase is complete for manifest
`public-sample-20260616T165835Z`. It verified that the train split contains
118 SFT rows, including 21 form-fill repair rows and 4 blocked-payment repair
rows, and prepared distinct public-safe runtime templates for
`a100-current-train-split-sft-retry`.

The project now needs one bounded A100 SFT retry to determine whether training
on the current 118-row train split changes held-out strict metrics, especially
the dev safety false negatives noted in the current baseline.

## What Changes

- Run fresh A100 SSH, GPU occupancy, disk/root, dependency, and manifest
  preflight before creating private overrides or launching training.
- Run one private SFT training job on the current formal public train split if
  safe GPU placement is available.
- Run dev/test prediction-only generation with the new private adapter.
- Run strict dev/test contract evaluation with the existing evaluator.
- Import only sanitized public-safe evidence: metadata summary, dev/test
  metrics, manifests, leak scans, comparison table, and a concise Human Brief.
- Preserve strict `contract_exact_match` and strict `slot_f1` as public headline
  metrics; keep `slot_f1_soft` diagnostic-only.
- Non-goals: DPO, GRPO, prompt changes, evaluator relaxation, semantic
  equivalence scoring, slot normalization, prediction repair/replacement,
  public checkpoint/adapter release, production-readiness claims, private-corpus
  claims, or live-browser benchmark claims.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `supervised-contract-tuning`: authorize and bound one private A100 SFT retry
  using the current formal public train split after readiness evidence exists.
- `contract-evaluation`: authorize and bound sanitized dev/test strict
  prediction evidence for the resulting private adapter.

## Impact

- Affected configs: `configs/sft-a100-current-train-split-retry*.json`.
- Affected remote execution: A100 SFT and prediction-only commands under the
  approved private project root.
- Affected public evidence: a new sanitized evidence directory under
  `reports/public-sample/` and a Human Brief under `docs/human-briefs/`.
- Affected specs: `supervised-contract-tuning` and `contract-evaluation`.
