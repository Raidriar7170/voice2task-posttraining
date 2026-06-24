# Copy-shadow false-trust diagnosis

Decision: `SOURCE_ATTESTATION_HARDENED_SCOPE_REDUCTION_REQUIRED`.

This is an offline, public-safe re-audit of committed challenge artifacts. It does not rerun predictions, train, modify policy v1, repair predictions, or enable runtime enforcement.

## Counts

- Historical source-attested exact input count: `64`
- Gold-correct among source-attested exact: `48`
- Source-attested but gold-mismatch cases: `16`
- Normalized-equivalent collision downgrades: `6`
- Post-diagnosis source_attested_exact count: `58`
- Execution eligible count: `0`

## Policy-v2 proposal

- `search:search_web:query`: `OBSERVE_LIMITED`
- `form_fill:fill_form:field`: `PROPOSE_DISABLE`
- `extract:extract_page:target`: `OBSERVE_ENABLED`

Recommended next change: `design-copy-shadow-scope-policy-v2`.
