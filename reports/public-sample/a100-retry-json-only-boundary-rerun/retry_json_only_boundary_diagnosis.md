# A100 retry JSON-only boundary diagnosis

Status: train-internal A100 diagnostic rerun after local retry JSON-only prompt hardening. This is not a benchmark, not a release, and no held-out generalization claim is made.

## Result

The rerun produced `3` train predictions from the private A100 adapter path. The stricter retry JSON-only prompt constraints were visible in metadata/prompt evidence, but retry attempts still produced prose/Markdown-wrapped JSON fragments for `3/3` rows.

Strict final-contract `json_valid_rate=0.0000` and `contract_exact_match=0.0000` remain unchanged from the bounded prior A100 stop-boundary rerun.

## Boundary Observation

Raw attempts were JSON objects for `3/3` rows but remained schema-invalid. Retry attempts were `json_fragment_object` for `3/3` rows; the strict retry parser rejected these fragments instead of extracting embedded contracts.

## Interpretation

- Prompt-policy visibility improved locally and is present in the A100 prediction metadata.
- Model behavior did not improve on this bounded train split: wrapper/preamble/suffix text still surrounds the retry JSON fragment.
- This does not prove model recovery, model quality improvement, production readiness, or held-out generalization.
- Do not describe the embedded JSON fragments as valid predictions; strict final metrics remain the source of truth.
