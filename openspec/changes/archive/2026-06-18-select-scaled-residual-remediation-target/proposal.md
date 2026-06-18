# select-scaled-residual-remediation-target

## Why

The scaled current-123 adapter residual-cluster inspection shows 29 strict
residual clusters and 321 residual rows, but it intentionally stopped before
choosing a remediation target.

Before adding data, changing policy, retraining, or retrying prediction, the
project needs a bounded target-selection evidence pack that decides which
cluster should be addressed first and records why other high-ranked clusters
are deferred.

## What Changes

- Generate a public-safe scaled residual remediation target-selection report
  from the committed scaled residual-cluster inspection evidence.
- Select the first remediation target using strict residual cluster evidence,
  with `contract_exact_match` and strict `slot_f1` as authoritative metrics.
- Record deferred high-ranked clusters and their deferral reasons, especially
  safety-sensitive blocked-payment residuals.
- Update `CONTEXT.md`, `reports/final_status.md`, and a concise Chinese Human
  Brief with the selected target and recommended next phase.
- Add focused tests for source-boundary preservation, selected target fields,
  deferred-target rationale, claim boundaries, and public-safe artifacts.
- Archive this OpenSpec change after validation.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `contract-evaluation`: add requirements for public-safe scaled residual
  remediation target selection from cluster-inspection evidence.

## Impact

- Affected evidence:
  `reports/public-sample/scaled-residual-remediation-target-selection/`.
- Affected docs: `CONTEXT.md`, `reports/final_status.md`, and a new Human Brief.
- Affected tests: focused scaled residual target-selection tests.
- No A100 job, training, prediction rerun, data materialization, prompt change,
  evaluator relaxation, semantic-equivalence scoring, slot normalization,
  prediction repair, DPO/GRPO run, checkpoint release, adapter release, public
  full-corpus release, production-readiness claim, or live-browser benchmark
  claim.
