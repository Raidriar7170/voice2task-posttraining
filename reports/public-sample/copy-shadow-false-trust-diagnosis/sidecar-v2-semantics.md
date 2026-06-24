# Sidecar v2 source-attestation semantics

`source_attested_exact` means only that the predicted slot value has a unique raw exact span in the public source input after deterministic validation. It is not semantic correctness.

Historical `trusted_provenance` remains a deprecated compatibility alias for committed v1 artifacts. New diagnosis artifacts use `source_attested_exact` and keep `execution_eligible=false`.

Online-style semantics keep `semantic_correctness=unknown`. Gold correctness appears only in offline diagnosis outputs that explicitly read committed gold contracts.

Normalized-equivalent matches remain candidate-only. If one raw exact span has multiple normalized equivalent source candidates, the diagnosis emits `AMBIGUOUS_NORMALIZATION_COLLISION`, sets `source_attested_exact=false`, and leaves `execution_eligible=false`.

Current diagnosis decision: `SOURCE_ATTESTATION_HARDENED_SCOPE_REDUCTION_REQUIRED`.
