## Why

The reviewed slot value generalization candidates are now materialized, but they are not yet learning evidence. Before merging them into the formal public sample or broadening data, we need a small candidate-only SFT probe that verifies the training path selects exactly those candidate rows and that any A100 execution status is recorded honestly.

This phase keeps the formal public sample unchanged while preparing and validating a bounded 7B probe surface for the 12 candidate SFT rows.

## What Changes

- Add a candidate-only SFT manifest that points to the materialized candidate SFT rows instead of the formal public sample rows.
- Add 7B A100 SFT and prediction config templates for a slot value candidate probe.
- Add a public-safe local dry-run/preflight evidence report that records candidate row selection, A100 dependency status, GPU preflight status, and non-claims.
- Add tests that prove the probe uses only candidate rows, does not mutate formal public sample files, and does not claim held-out recovery.
- Generate a concise Chinese Human Brief with project-stage progress and next decision boundaries.

## Non-Goals

- Do not merge candidates into `data/public-samples/seed_traces.jsonl`.
- Do not rebuild the formal public sample SFT/DPO artifacts.
- Do not run DPO/GRPO or generate DPO hard negatives.
- Do not relax evaluator rules, normalize predictions, or promote soft slot F1 or semantic equivalence as primary.
- Do not claim model recovery, held-out recovery, private-corpus generalization, production readiness, adapter release, checkpoint release, or live-browser benchmark improvement.
- Do not publish raw A100 logs, checkpoints, adapters, caches, host details, SSH details, private paths, tokens, or private corpus rows.
- Do not expand into generic chat fine-tuning, skill routing, GUI action policy learning, first-phase GRPO, or public release of the full local corpus.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `supervised-contract-tuning`: add a bounded candidate-only SFT probe path for reviewed slot value generalization candidates.
- `contract-evaluation`: add public-safe reporting boundaries for candidate probe prep/execution evidence.

## Impact

- `configs/`: add candidate-only 7B SFT and prediction templates.
- `data/public-samples/`: add a candidate-only manifest that references candidate SFT rows.
- `src/voice2task/reports.py`: add a report writer for candidate SFT probe evidence.
- `src/voice2task/cli/report.py`: add a CLI command to write the evidence report from dry-run/preflight inputs.
- `tests/`: add focused tests for row selection, config boundaries, report claims, and committed evidence.
- `reports/public-sample/`: add the candidate SFT probe evidence pack.
- `docs/human-briefs/`: add the phase brief.
