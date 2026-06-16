## Why

The confirmation-marker coverage assessment shows that the existing legacy remediation chain covers only 3 field labels while the current policy surface spans 12 source families and still has 27 observed normalized-command residual incidences. Before adding data, changing prompts, or training, the project needs a bounded candidate-design phase that expands confirmation-marker coverage from the observed family surface without making recovery claims.

## What Changes

- Add a deterministic confirmation-marker extension design that reads committed public-safe coverage evidence and proposes additional candidate cases for uncovered or thinly covered source-family/field surfaces.
- Publish JSON, Markdown, and manifest artifacts under `reports/public-sample/` describing the proposed candidate cases, represented field labels, source-family coverage, and unsupported changes.
- Generate a concise Human Brief for the design phase.
- Preserve design-only boundaries: no new candidate rows, no seed/public-sample/SFT/DPO mutation, no prompt change, no prediction run, no training, no evaluator relaxation, no prediction repair/re-score, and no checkpoint/adapter release.

## Capabilities

### New Capabilities

### Modified Capabilities

- `contract-evaluation`: require a public-safe confirmation-marker coverage extension design before materializing any additional confirmation-marker candidate rows or launching training.

## Impact

- Affected code: deterministic evaluation/report helpers and a CLI entry point for the extension design.
- Affected reports: add a new public-safe design report under `reports/public-sample/`.
- Affected tests: add focused tests for source coverage, candidate-design boundaries, source count consistency, no-mutation/no-recovery claims, and public-safety scanning.
- Affected specs: extend `contract-evaluation` with a confirmation-marker extension-design evidence requirement.
- Non-goals: generic chat fine-tuning, skill routing, GUI action policy learning, first-phase GRPO, public release of the full local corpus, candidate materialization, formal public sample mutation, prompt change, evaluator relaxation, prediction repair, prediction run, SFT/DPO/GRPO training, checkpoint release, adapter release, production readiness, private-corpus generalization, public full-corpus release, or live-browser benchmark improvement claims.
