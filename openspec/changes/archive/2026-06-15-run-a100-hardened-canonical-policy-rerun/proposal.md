## Why

The merged slot-value held-out run still leaves strict dev/test residuals after
the prompt was hardened for canonical clarify and unsafe-payment wording. This
phase verifies whether that hardened prompt policy changes the existing 7B
adapter's train/dev/test prediction behavior without retraining, changing data,
or relaxing the evaluator.

## What Changes

- Add prediction-only A100 7B config templates for train/dev/test using the
  existing merged slot-value adapter.
- Run, when remote placement is safe, split-specific predictions and strict
  contract metrics with the current hardened prompt policy.
- Publish a public-safe evidence pack that compares the rerun against the
  prior merged slot-value held-out evidence.
- Record whether the prediction metadata proves the hardened canonical prompt
  flags were visible during the rerun.
- Generate a concise Chinese Human Brief for this phase.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `supervised-contract-tuning`: support a bounded prediction-only A100 rerun
  using an existing 7B adapter and current hardened prompt policy.
- `contract-evaluation`: publish public-safe hardened prompt rerun evidence
  with strict metrics, prompt-flag provenance, and no recovery overclaim.

## Impact

- `configs/`: new A100 prediction-only templates with private placeholders.
- `src/voice2task/reports.py` and `src/voice2task/cli/report.py`: sanitized
  hardened prompt rerun evidence writer.
- `tests/`: focused config, report, and public-safety coverage.
- `reports/public-sample/a100-hardened-canonical-policy-rerun/`: imported
  public-safe evidence or blocked status.
- `docs/human-briefs/`: Chinese review companion for this phase.

Non-goals: generic chat fine-tuning, skill routing, GUI action policy learning,
first-phase GRPO, DPO training, SFT retraining, data expansion, evaluator
relaxation, prediction repair, public release of adapters/checkpoints, public
release of the full local/private corpus, production-readiness claims, and
live-browser benchmark improvement claims.
