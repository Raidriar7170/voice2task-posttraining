# Copy-Shadow Source Attestation Boundary

This note defines the claim boundary for copy-shadow source attestation after the
`diagnose-copy-shadow-false-trust-before-naturalistic-v2` phase.

## Definition

`source_attested_exact=true` means the predicted slot value has one unique raw
exact span in the public source input, with matching source hash, offsets,
roundtrip slice, policy-enabled scope, and prediction-value hash.

It does not mean:

- semantic correctness
- gold correctness
- task correctness
- slot accuracy
- execution eligibility
- runtime enforcement readiness
- model improvement
- production or safety readiness

Historical `trusted_provenance` remains a deprecated compatibility alias for
committed v1 sidecars and audits. New diagnosis artifacts use
`source_attested_exact` to avoid implying trust beyond source-span attestation.

## Online And Offline Split

Online-style sidecar semantics are source-only:

- `source_attested_exact` can be derived from source span evidence.
- `semantic_correctness` remains `unknown`.
- `execution_eligible` remains `false`.
- Gold correctness must not appear in online sidecars.

Offline diagnosis artifacts may read committed gold contracts and evaluation
audits. They can report `offline_gold_mismatch`, but that is an audit result,
not a runtime decision input.

## Normalization Collision Boundary

Normalized-equivalent matches remain candidate-only. If a predicted value has
one raw exact source span but multiple normalized-equivalent source candidates,
the diagnosis downgrades the event to:

```text
AMBIGUOUS_NORMALIZATION_COLLISION
```

The downgraded event sets `source_attested_exact=false`,
`execution_eligible=false`, and keeps normalized provenance out of the trusted
surface.

The diagnosis uses the deterministic rule
`nfkc_casefold_strip_space_punct_symbol` for collision auditing. This is an
offline audit rule and does not enable normalized trusted provenance.

## Known Limitations

Source-absent substitutions cannot be made safe by exact source attestation:
the wrong value can still appear elsewhere in the input.

Partial and overlong spans can be technically source-attested while selecting
the wrong semantic unit.

Field slots in `form_fill:fill_form:field` mix field name, value, and DOM/schema
resolution risks. Exact text copy alone is too weak for further integration.

## Current Diagnosis

Current diagnosis bundle:
`reports/public-sample/copy-shadow-false-trust-diagnosis/summary.json`

Decision:
`SOURCE_ATTESTATION_HARDENED_SCOPE_REDUCTION_REQUIRED`

Recomputed counts:

- historical source-attested exact input count: 64
- source-attested and gold-correct: 48
- source-attested but gold-mismatch: 16
- normalized-equivalent collision downgrades: 6
- post-diagnosis source-attested exact count: 58
- execution eligible count: 0

Per-scope proposal:

- `form_fill:fill_form:field`: `PROPOSE_DISABLE`
- `search:search_web:query`: `OBSERVE_LIMITED`
- `extract:extract_page:target`: `OBSERVE_ENABLED`

Recommended next change:
`design-copy-shadow-scope-policy-v2`

This recommendation is a proposal boundary only. It does not create policy v2,
naturalistic challenge v2, runtime enforcement, training, data expansion,
action enablement, or normalized trusted provenance.
