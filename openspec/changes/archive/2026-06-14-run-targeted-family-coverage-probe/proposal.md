## Why

Current 7B tiny-adapter held-out evidence has `contract_exact_match=0.0` on dev and test. The latest family strategy diagnosis shows the failed held-out families have train analog coverage in the public sample, but the actual tiny training subset only covered the search/weather family. We need one bounded A100 probe that tests targeted family coverage before broad data scaling or DPO.

## What Changes

- Add a public-safe targeted SFT family coverage probe that trains only on the four train analog source families for the current held-out residual families.
- Add split-specific prediction templates for train/dev/test using the targeted probe adapter.
- Add local validation that the targeted training config selects exactly the intended source families and does not mutate the public dataset.
- Import sanitized A100 evidence if the remote run completes, including metrics, sidecars, manifest, report, and leak-scan summaries.
- Preserve strict interpretation boundaries: no checkpoint release, no adapter release, no production-readiness claim, no full private-corpus claim, and no live-browser benchmark claim.
- Do not run DPO, GRPO, prompt-policy changes, evaluator relaxation, semantic rescoring, GUI action policy learning, skill routing, or generic chat fine-tuning in this phase.

## Capabilities

### New Capabilities

### Modified Capabilities

- `supervised-contract-tuning`: Add targeted source-family SFT training/prediction support for the public held-out family coverage probe.
- `contract-evaluation`: Add public-safe evidence requirements for interpreting the targeted family coverage probe.

## Impact

- `configs/`: new or adjusted public-safe A100 SFT and prediction templates for targeted family coverage.
- `src/voice2task/training.py`: source-family row selection metadata for SFT training.
- `src/voice2task/cli/train.py`: no new command is expected; the existing SFT and prediction commands should remain the entrypoints.
- `tests/`: focused tests for targeted family selection, config boundaries, and evidence interpretation.
- `reports/public-sample/`: sanitized evidence pack for the targeted probe if A100 execution completes, or a blocked/preflight evidence pack if it cannot safely run.
- `docs/human-briefs/`: concise Chinese phase brief.
