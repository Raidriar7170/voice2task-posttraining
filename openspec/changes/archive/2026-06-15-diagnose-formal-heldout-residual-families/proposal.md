## Why

The current formal public held-out evidence shows partial full-contract behavior:
dev/test strict exact match is `0.3043 / 0.2899`, while JSON validity is
`1.0000`. The next decision should not be more training, DPO, data generation,
or evaluator changes until the residual rows are grouped by family, field path,
and mismatch category.

## What Changes

- Add a formal-public-heldout residual/family diagnosis for the current
  `a100-formal-public-heldout-prediction` evidence pack.
- Add a CLI/reporting path that reads existing dev/test gold rows, predictions,
  and formal held-out manifest, then writes public-safe residual JSON,
  Markdown, and manifest artifacts.
- Generate a concise Chinese Human Brief explaining the residual distribution
  and the recommended bounded next step.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `contract-evaluation`: add a formal public held-out residual/family diagnosis
  requirement that preserves strict metric boundaries and blocks automatic
  remediation.

## Impact

- Affected code: `src/voice2task/evaluation.py`,
  `src/voice2task/reports.py`, `src/voice2task/cli/eval.py`.
- Affected evidence: new
  `reports/public-sample/formal-heldout-residual-family-diagnosis/` artifacts.
- Affected docs: one Human Brief HTML and OpenSpec archive.
- Non-goals: no dataset mutation, no SFT/DPO training, no prediction rerun, no
  evaluator semantic change, no prediction repair, no soft-metric promotion, no
  checkpoint/adapter release claim, no production-readiness claim, and no
  live-browser benchmark claim.
