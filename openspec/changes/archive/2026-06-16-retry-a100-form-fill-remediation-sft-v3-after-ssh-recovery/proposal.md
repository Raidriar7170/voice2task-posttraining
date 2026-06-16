## Why

The previous `run-a100-form-fill-remediation-sft-v3` phase was blocked before
GPU inspection because the configured A100 SSH alias timed out. Connectivity is
now reported as restored, so the project needs a bounded retry that redoes
preflight from scratch and either produces sanitized SFT v3 held-out evidence
or records a new blocked/failed status honestly.

## What Changes

- Re-run A100 SSH, GPU occupancy, disk, approved-root, and dependency preflight.
- Create repo-external private overrides only if preflight is safe.
- Run the existing `form_fill` remediation SFT v3 config on the current public
  train split if a safe idle GPU is available.
- Run dev/test prediction-only generation and strict evaluation with the new
  private adapter.
- Import only sanitized evidence into a new public-safe evidence directory.
- Preserve the previous blocked preflight archive as historical evidence rather
  than overwriting it.
- Non-goals: DPO, GRPO, evaluator relaxation, semantic-equivalence scoring,
  prediction repair/replacement, public checkpoint or adapter release,
  production-readiness claims, and live-browser benchmark claims.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `supervised-contract-tuning`: require a fresh A100 preflight when retrying
  after a blocked SFT v3 attempt.
- `contract-evaluation`: require separate sanitized retry evidence and clear
  comparison against the previous blocked attempt and current strict baseline.

## Impact

- Affected remote execution: A100 SFT and prediction-only commands under the
  approved private project root.
- Affected public evidence: new retry evidence under `reports/public-sample/`
  plus a Human Brief and final-status/context refresh.
- Affected OpenSpec capabilities: `supervised-contract-tuning` and
  `contract-evaluation`.
