## Context

The current formal public sample manifest is `public-sample-20260616T165835Z` with 100 seed rows, 256 SFT rows, 864 DPO pairs, and split counts of train 118, dev 69, and test 69. The latest SFT v3 model-quality evidence is bound to the previous manifest, `public-sample-20260616T074315Z`, where dev/test each had 69 rows.

The blocked-payment repair materialization added train-only repair rows. Because dev/test row counts did not change, this phase may produce metrics close to the previous SFT v3 retry, but it is still required to bind current model evidence to the current manifest boundary. It must not be described as training, model recovery, or safety improvement from the repair rows.

## Goals / Non-Goals

**Goals:**

- Verify A100 connectivity, safe GPU placement, approved remote root, and private SFT v3 adapter availability.
- Run prediction-only dev/test exports against the current formal public sample manifest with the existing SFT v3 adapter.
- Evaluate predictions with the existing strict contract ladder.
- Import only sanitized predictions, sidecars, metadata, metrics, manifest/report files, and leak scans into git.
- Refresh `CONTEXT.md`, `reports/final_status.md`, and a concise Chinese Human Brief with current-manifest results and claim boundaries.

**Non-Goals:**

- No SFT, DPO, GRPO, prompt update, dataset mutation, evaluator relaxation, semantic-equivalence scoring, slot normalization, prediction repair, or prediction replacement.
- No public release of checkpoints, adapters, raw logs, private overrides, private paths, model caches, host details, SSH details, tokens, or full private corpus.
- No production-readiness, held-out recovery, private-corpus generalization, or live-browser benchmark claim.

## Decisions

1. Use the existing SFT v3 adapter rather than training a new adapter.
   - Rationale: this phase isolates the manifest-boundary update and answers the current-model question.
   - Alternative considered: immediately train on the 118-row train split. Rejected because blocked-payment repair rows were just materialized and need a current-manifest baseline first.

2. Publish to a new evidence directory.
   - Rationale: the new manifest boundary must not overwrite the previous SFT v3 retry or the older prediction-only baseline.
   - Alternative considered: update the previous SFT v3 retry directory. Rejected because it would blur which manifest produced which metrics.

3. Record `source_adapter_runtime` as `a100-form-fill-remediation-sft-v3`.
   - Rationale: the generic formal held-out report writer previously assumed the older merged-slot adapter runtime. This phase needs the report to identify the actual SFT v3 source adapter.
   - Alternative considered: use the existing hardcoded source. Rejected because it would produce misleading evidence.

4. Fail closed when A100 execution is unsafe.
   - Rationale: no model-quality metric is better than a fabricated or unsafe one.
   - Alternative considered: fixture-mode prediction. Rejected because it does not measure the private adapter.

## Risks / Trade-offs

- GPU occupancy or remote access may be unsafe -> record blocked evidence without predictions or model-quality claims.
- Metrics may be unchanged because dev/test rows did not change -> report that as current-manifest evidence, not as improvement.
- Sanitized sidecars may still contain private-looking text -> run leak scans over evidence and docs before commit.
- The source adapter is private -> keep adapter/checkpoint/log/cache paths out of committed artifacts and use public-safe runtime labels.
