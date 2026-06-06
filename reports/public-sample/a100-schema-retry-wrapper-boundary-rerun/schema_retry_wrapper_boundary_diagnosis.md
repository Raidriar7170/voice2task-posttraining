# A100 schema retry wrapper-boundary diagnosis

Status: retry wrapper-boundary prompt constraints reached the A100 prediction metadata, but strict schema recovery was not observed.

- Strict final `json_valid_rate`: 0.0000
- Strict final `contract_exact_match`: 0.0000
- Raw whole JSON object count: 3/3
- Raw missing `task_type`: 3/3
- Retry prose/Markdown wrapper count: 3/3
- Retry forbidden preface visible count: 2/3
- Retry trailing analysis visible count: 3/3
- Validated output schema-valid rows: 0/3

The local retry-wrapper boundary repair is visible as prompt metadata, but the private adapter still emits wrapped retry completions. This is negative evidence, not model recovery evidence. No parser relaxation, prediction repair, slot normalization, semantic-equivalence scoring, or metric relaxation was performed.
