## Why

The recovered adapter challenge showed that exact source attestation can be technically valid while still selecting the wrong semantic slot value. Before any naturalistic v2 challenge or policy v2 work, the project needs a bounded diagnosis that separates source provenance from semantic correctness and hardens normalized-collision handling without changing frozen predictions, gold, policy v1, or runtime behavior.

## What Changes

- Add an offline false-trust diagnosis over the committed `copy-shadow-template-disjoint-challenge-v1` adapter-evaluation artifacts.
- Recompute source-attested-but-gold-mismatch cases from committed challenge rows, predictions, online sidecars, and evaluation audits rather than copying prior summary counts.
- Introduce the `source_attested_exact` terminology and sidecar v2 semantics proposal while preserving historical `trusted_provenance` artifacts as compatibility inputs.
- Add deterministic normalized-equivalent collision detection that can downgrade raw-exact source attestation to `AMBIGUOUS_NORMALIZATION_COLLISION` during re-audit.
- Produce a compact public-safe evidence bundle under `reports/public-sample/copy-shadow-false-trust-diagnosis/`.
- Update documentation and truth surfaces with conservative claim boundaries and a single next-change recommendation.

## Capabilities

### New Capabilities
- `copy-shadow-false-trust-diagnosis`: Offline diagnosis and observe-only hardening of source-attested-but-gold-mismatch challenge evidence before policy v2 or naturalistic v2 work.

### Modified Capabilities
- None.

## Impact

- Adds offline diagnosis code, tests, and a report generation script.
- Adds public-safe report artifacts, a source-attestation boundary document, and a Chinese Human Brief.
- Does not train, rerun predictions, modify model weights, modify prompts or decoding, change `copy-backed-scope-policy-v1`, change challenge rows/gold/tags, change historical predictions/sidecars/evaluation audits, change BrowserTaskContract V1, change ContractCoreV2, modify evaluators, or enable runtime enforcement.
