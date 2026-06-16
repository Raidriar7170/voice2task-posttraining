## Why

The project has a newer A100 recovery prediction-only evidence pack for manifest
`public-sample-20260616T074315Z`, but the committed residual-family diagnosis and
target-selection artifacts still point at the prior formal held-out evidence
boundary. This creates a documentation/evidence drift risk exactly at the moment
the project is being closed down as a public-facing baseline.

## What Changes

- Refresh formal held-out residual-family diagnosis evidence so it reads from
  `reports/public-sample/a100-formal-public-heldout-prediction-after-a100-recovery/`.
- Refresh formal held-out remediation target-selection evidence so its source
  manifest, strict metrics, and ranked family results are tied to the same
  current evidence boundary.
- Refresh formal held-out residual-cluster inspection evidence because it is a
  direct downstream view of the residual-family diagnosis.
- Refresh the confirmation-marker coverage artifact's current residual evidence
  reference while preserving its legacy policy/remediation provenance. This
  avoids rewriting already-materialized candidate lineage into a circular source.
- Update tests to fail closed if the committed diagnosis or target-selection
  reports drift back to an older manifest.
- Add a short Human Brief for this evidence-only refresh phase.
- Preserve the existing boundary: no training, no prediction rerun, no data
  mutation, no evaluator relaxation, no slot normalization, no checkpoint or
  adapter release, and no live-browser benchmark claim.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `contract-evaluation`: require committed formal residual-family diagnosis and
  remediation target-selection artifacts to identify the current formal
  held-out evidence manifest when refreshed after a newer prediction-only run.

## Impact

- Affected code/tests: residual-family diagnosis tests, target-selection tests,
  and possibly small helper behavior if the current evidence layout requires it.
- Affected reports: `reports/public-sample/formal-heldout-residual-family-diagnosis/`
  `reports/public-sample/formal-heldout-residual-cluster-inspection/`, and
  `reports/public-sample/formal-heldout-remediation-target-selection/`, plus
  the source-evidence pointer in
  `reports/public-sample/form-fill-confirmation-marker-coverage/`.
- Affected documentation: one Human Brief under `docs/human-briefs/`.
- No training configs, model weights, public sample rows, DPO data, evaluator
  metric definitions, or private A100 artifacts are changed.
