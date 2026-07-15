## Why

The current formal public manifest binds one mixed SFT artifact containing train, dev, and public-test rows, so a train-only consumer cannot satisfy a fail-closed read-scope contract without opening an artifact that also contains prohibited splits. A dedicated deterministic train-only artifact is required before any future development SFT screen can be considered for separate authorization.

## What Changes

- Extend the canonical public-sample builder to emit `sft_train_public_sample.jsonl` as the unchanged ordered subsequence of current formal SFT rows whose split is exactly `train`, using the repo-relative reference only for the canonical formal output and a manifest-relative basename for every other build location.
- Bind the dedicated artifact in `manifest_public_sample.json` with a repo-relative path, exact row count, split declaration, canonical-JSONL flag, and SHA-256 over final bytes.
- Validate the binding fail closed for path, symlink, hash, row-count, duplicate-ID, non-train-row, and mixed-subsequence drift; ordinary `public=True` validation cannot downgrade by deleting both binding halves.
- Materialize the current 282-row train-only artifact without changing the existing mixed SFT, DPO, seed, population counts, split counts, manifest ID, or generated-at value.
- Regenerate the CURRENT split-integrity report against the live manifest while preserving historical manifest and split-report hash consumers through immutable snapshots instead of rewriting historical evidence.
- Keep all clean-evaluation status facts unchanged and stop before training, prediction, evaluation, A100 use, commit, push, archive, or merge.
- Explicit non-goals: no generic chat fine-tuning, skill routing, GUI action-policy learning, DPO, GRPO, model loading, public-test evaluation, lockbox access, clean-population materialization, full public corpus release, checkpoint/adapter release, or model/metric improvement claim.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `voice2task-dataset-preparation`: require public-sample builds to emit and integrity-bind a deterministic train-only SFT artifact while preserving the existing mixed population and historical evidence identities.

## Impact

- Affects `src/voice2task/dataset.py`, dataset validation, focused data tests, and the current formal public manifest/artifact set.
- Adds one committed public-safe JSONL artifact containing only rows already present in the current formal train split.
- Updates the current truth-surface manifest hash and adds historical manifest snapshot routing where old audits intentionally bind the prior manifest bytes.
- Does not change training, prediction, evaluation, model, prompt, decoder, schema semantics, or clean-evaluation readiness.
