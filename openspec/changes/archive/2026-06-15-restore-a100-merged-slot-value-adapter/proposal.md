## Why

The hardened canonical policy rerun is blocked because the required
`a100-merged-slot-value-heldout-eval` adapter is missing from the remote A100
project root. This phase restores that prerequisite adapter path or regenerates
it from the already-approved merged slot-value SFT config so the next
prediction-only evaluation can run without changing data or evaluator semantics.

## What Changes

- Check the approved A100 project root for an existing reusable merged
  slot-value adapter.
- If no reusable adapter exists, run the existing merged slot-value SFT training
  config on an idle A100 using only `<approved_remote_root>` paths.
- Publish a public-safe adapter restore/regeneration evidence pack with
  sanitized dependency, GPU-preflight, adapter-file, and training-status fields.
- Generate a concise Chinese Human Brief for this prerequisite phase.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `supervised-contract-tuning`: allow a bounded restore/regenerate phase for a
  previously approved private A100 adapter path.
- `contract-evaluation`: publish public-safe prerequisite evidence without
  implying new prediction metrics or model recovery.

## Impact

- `src/voice2task/reports.py` and `src/voice2task/cli/report.py`: adapter
  restore/regeneration evidence writer.
- `tests/`: focused coverage for public-safe evidence, blocked status, and
  claim boundaries.
- `reports/public-sample/a100-merged-slot-value-adapter-restore/`: sanitized
  prerequisite evidence.
- `docs/human-briefs/`: Chinese review companion for this phase.

Non-goals: data expansion, evaluator changes, hardened prompt prediction rerun,
DPO/GRPO, public adapter/checkpoint release, private-corpus generalization,
production-readiness claims, and live-browser benchmark improvement claims.
