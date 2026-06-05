## Why

The local `repair-confirmation-required-emission` phase made `confirmation_required` explicitly visible as a required boolean in the shared SFT/prediction prompt and low-risk weather/search example. The next smallest evidence step is one authorized A100 prediction-only train-split rerun to test whether this local repair changes the real private-adapter outputs that previously omitted `confirmation_required` in all three train rows.

## What Changes

- Run one bounded A100 prediction-only train-split rerun using the current confirmation-required prompt, strict whole-string raw/retry parser, and existing private train-split adapter.
- Keep `prediction_split=train`, `overfit_diagnostic=true`, `generalization_claim=false`, `schema_retry_enabled=true`, greedy decoding, and no schema repair/coercion.
- Import only sanitized public-safe evidence: prediction metadata, predictions, prompt snapshot, raw decoded summary, generation trace, metrics, schema guard summary, confirmation-required diagnosis, manifest, reports, leak scans, and Human Briefs.
- Compare narrowly against `reports/public-sample/a100-route-ontology-train-split-rerun/` as the pre-confirmation-required-repair baseline.
- Preserve the result honestly whether schema/confirmation recovery improves, remains partial, or stays `0/3`.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `supervised-contract-tuning`: add an explicitly authorized A100 confirmation-required train-split prediction rerun path after local confirmation-required prompt repair.
- `contract-evaluation`: add public-safe evidence requirements and non-claim boundaries for the confirmation-required A100 rerun.

## Impact

- Affected runtime path: `voice2task.cli.train sft-predict` on A100 with a repo-external private adapter config and approved private output root.
- Affected evidence: new public-safe report directory under `reports/public-sample/a100-confirmation-required-train-split-rerun/` and Chinese Human Briefs under `docs/human-briefs/`.
- Non-goals: no generic chat fine-tuning, no skill routing, no GUI action policy learning, no first-phase GRPO, no public release of the full local corpus, no SFT/DPO training, no dev/test or full-public-sample rerun, no checkpoint or adapter release, no production-readiness claim, no held-out generalization claim, no public full-corpus release, and no live-browser benchmark improvement claim.
