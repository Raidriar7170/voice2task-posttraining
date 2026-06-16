## Why

The formal public sample now includes the 9 reviewed train-only `form_fill` remediation candidates, but the committed held-out prediction evidence still reflects the previous manifest boundary. A prediction-only held-out rerun is needed to measure the new formal sample boundary without making a training, evaluator, or recovery claim.

## What Changes

- Run prediction-only formal public held-out evaluation for the updated public manifest on `dev` and `test`.
- Commit only sanitized public-sample prediction sidecars, metrics, manifests, reports, and diagnostics.
- Add a Human Brief summarizing the new held-out evidence and residual families.
- Preserve strict boundaries: no SFT/DPO/GRPO training, no evaluator metric changes, no checkpoint/adapter release, no production readiness claim, and no held-out recovery claim unless strict metrics support it.

## Capabilities

### New Capabilities

### Modified Capabilities

- `contract-evaluation`: require formal held-out prediction evidence to record the public manifest boundary used for reruns after formal public-sample merges.

## Impact

- Affected configs: formal public held-out prediction configs already pointing at the updated manifest ID.
- Affected runtime: A100 prediction-only execution using the existing private adapter path resolved outside git.
- Affected reports: refreshed `reports/public-sample/a100-formal-public-heldout-prediction/{dev,test}/` evidence and a concise Human Brief.
- Affected tests: focused evidence/report tests may need updated expected manifest IDs, counts, and residual-family assertions.
- Non-goals: generic chat fine-tuning, skill routing, GUI action policy learning, first-phase GRPO, public release of the full local/private corpus, any new training run, evaluator relaxation, checkpoint/adapter release, production readiness claims, live-browser benchmark improvement claims, or private-corpus generalization claims.
