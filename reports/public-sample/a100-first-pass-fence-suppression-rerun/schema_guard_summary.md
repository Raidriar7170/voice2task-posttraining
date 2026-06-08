# A100 first-pass fence-suppression schema guard summary

## Summary
- prediction_count: `3`
- markdown_wrapped_prediction_count: `0`
- validated_output_schema_valid_count: `3`
- strict_final_json_valid_rate: `1.0`
- strict_final_contract_exact_match: `0.6666666666666666`
- slot_exact_match_residual_rows: `1`

## Boundary
- Strict whole-object parser/evaluator semantics are unchanged.
- No parser relaxation, fence stripping, prediction repair, re-score, slot normalization, or semantic-equivalence scoring was performed.
- This is train-split-only A100 prediction evidence and not a held-out generalization claim.
