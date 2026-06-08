## Why

The latest A100 search-query slot-policy rerun observed compact `slots.query` content in the decoded fragments, but every row was still wrapped in Markdown fences and strict schema-valid output stayed at `0/3`. The next safe step is a local diagnosis of that wrapper/boundary evidence so we can separate observed facts from hypotheses before deciding whether any future decoding change is worth user confirmation.

## What Changes

- Publish a public-safe local diagnosis pack for the A100 search-query slot wrapper boundary using only existing sanitized sidecars and public evidence.
- Record the observed raw-vs-retry wrapper symptoms, strict final metrics, and the evidence gaps that prevent overclaiming model recovery or boundary repair.
- Add focused tests and a concise Chinese Human Brief for the diagnostic phase.
- Do not run a new A100 prediction rerun, train a model, relax parsing, normalize slots, or reinterpret strict metrics.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `contract-evaluation`: publish local evidence that separates observed generation facts, wrapper symptoms, and boundary evidence gaps for the A100 search-query slot rerun without changing metrics or re-scoring predictions.
- `supervised-contract-tuning`: preserve the wrapper-boundary diagnostic step before any future decoding, instrumentation, or output-postprocessing change.

## Impact

- Affected evidence: `reports/public-sample/a100-search-query-slot-wrapper-boundary-diagnosis/`.
- Affected docs: `docs/human-briefs/`.
- Affected tests: focused evidence boundary tests for the diagnosis pack and its non-claims.
- No change to training, decoding, parser behavior, metrics, or release posture.
