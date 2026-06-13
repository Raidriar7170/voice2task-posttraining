## Why

The latest public-sample learning-signal evidence shows that canonical assistant targets are present in rendered SFT text, but true runtime label-mask evidence for the current `public-sample-20260613T072200Z` manifest remains unavailable. Before adding more data, launching another full A100 SFT rerun, or using DPO, the project needs a bounded diagnostic that verifies whether the current training objective actually places loss on assistant contract tokens and whether old runtime/overfit evidence is stale.

## What Changes

- Add a public-safe diagnostic that compares the current public manifest against prior runtime-label and tiny-overfit artifacts.
- Record whether runtime label evidence is fresh for the current manifest, stale, fixture-only, unavailable, or inspectable.
- Record prompt/assistant token-mask indicators when a fresh runtime label check artifact exists.
- Prepare a bounded tiny-overfit recommendation only after the runtime label evidence boundary is explicit.
- Generate a committed evidence pack under `reports/public-sample/runtime-label-tiny-overfit-diagnostic/` without copying private paths, raw rendered prompts, raw logs, checkpoints, adapters, caches, SSH details, host details, or private corpus rows.
- Generate a concise Chinese Human Brief for the phase.
- Do not run full SFT, DPO, GRPO, generic chat fine-tuning, skill routing, GUI action policy learning, checkpoint release, public full-corpus release, production deployment, or live-browser benchmark claims in this phase.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `supervised-contract-tuning`: require bounded current-manifest runtime label/tiny-overfit diagnostics before interpreting additional train-split reruns as SFT objective evidence.
- `contract-evaluation`: require a public-safe runtime-label/tiny-overfit diagnostic evidence pack with explicit freshness, claim boundaries, and next-step recommendation.

## Impact

- Code: likely `src/voice2task/training.py`, `src/voice2task/evaluation.py`, `src/voice2task/reports.py`, and CLI/report wiring.
- Tests: focused regression tests for current-manifest runtime-label freshness, stale prior evidence handling, bounded tiny-overfit recommendation, and public-safe evidence artifacts.
- Artifacts: OpenSpec change artifacts, public-safe report files, leak scan results, and one Human Brief HTML.
- Systems: local-only by default. A100/private runtime is not required unless a later explicitly bounded execution step is selected; any such work must remain under the approved private A100 project root and out of committed private artifacts.
