## Why

The local retry JSON-only boundary hardening phase proved that the retry prompt and metadata now expose stricter exact-output constraints, but it did not run the trained adapter. A bounded A100 prediction-only rerun is needed to observe whether the private adapter actually follows the stricter retry boundary on the 3-row train split.

## What Changes

- Run one A100 prediction-only train-split rerun with the existing private adapter and the stricter retry JSON-only prompt policy.
- Collect sanitized predictions, prompt snapshot, raw decoded summary, generation trace, metadata, strict metrics, schema guard summary, retry-boundary diagnosis, manifest, report, and leak scans.
- Compare only against `reports/public-sample/a100-generation-stop-reason-boundary-rerun/` and `reports/public-sample/tighten-retry-json-only-output-boundary/`.
- Preserve strict parser/evaluator semantics: wrapped retry fragments remain invalid unless the whole retry response is a valid Browser Task Contract JSON object.
- Make no training, adapter/checkpoint release, held-out generalization, production-readiness, live-browser benchmark, or model-quality claim.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `supervised-contract-tuning`: support a bounded A100 prediction-only rerun after retry JSON-only boundary hardening while keeping private runtime artifacts outside git.
- `contract-evaluation`: publish public-safe A100 retry-boundary rerun evidence that separates strict final metrics from retry-boundary observations and non-claims.

## Impact

- Affected runtime: A100 private prediction path using the existing private adapter and an explicitly selected idle GPU.
- Affected artifacts: new evidence pack under `reports/public-sample/a100-retry-json-only-boundary-rerun/`, archived OpenSpec change, synced specs, tests, and a Chinese Human Brief.
- No dependency changes, no training, no parser relaxation, no evaluator metric change, no prediction repair/re-score, no full-corpus public release, and no released checkpoint/adapter.
