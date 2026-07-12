# Public Split Integrity Audit

- Methodology: `voice2task.split_integrity.v1`
- Evidence status: `DEVELOPMENT_ONLY_SPENT`
- Input validation passed: `true`
- Input validation errors: 0
- Clean gate passed: `false`
- Inputs: 247 seed rows; 696 SFT rows; 2100 DPO pairs; train/dev/test = 282/207/207
- Historical rows mutated: `false`
- Historical metrics rescored: `false`

## Strict-zero gate

| check | count |
| --- | ---: |
| `cross_split_digit_template_signatures` | 8 |
| `heldout_exact_input_rows_overlapping_train` | 4 |
| `train_rows_with_dev_test_provenance` | 33 |

## Overlap inventory

| check | held-out rows | role |
| --- | ---: | --- |
| `exact_input` | 4 | strict-zero gate |
| `full_target_contract` | 33 | diagnostic-only |
| `normalized_command` | 120 | diagnostic-only |
| `slots` | 39 | diagnostic-only |
| `structural_contract` | 414 | diagnostic-only |

Digit-normalized seed templates: 8 cross-split signatures covering 140 seed rows.
Train provenance: 33 rows resolve to dev/test sources.

## Interpretation boundary

The current public dev/test boundary is development-only/spent, not blind, independent, or leakage-free evidence. Historical data and metrics remain preserved and were not recomputed.
Lexical/template/provenance checks do not establish semantic independence, natural-ASR provenance, or model quality. Repeated target and ontology signatures remain diagnostic-only.

## Sources

- `data/public-samples/seed_traces.jsonl` — `8fe5e75e9e0891b6824d7c142cbe15547267377420f8b3240414436265d15801`
- `data/public-samples/sft_public_sample.jsonl` — `4b677420f766555c04199f15f69f41f3b3ad36ad3cd5c33d2b40b0e3f8573587`
- `data/public-samples/dpo_public_sample.jsonl` — `b673dff3c1f598a250c8ed463be320fd2126b61a07e7672b83fbca4bae266ea8`
- `data/public-samples/manifest_public_sample.json` — `f866c173795e97953b1dec85611b405867d0a29497910282f99d399f109cda95`
