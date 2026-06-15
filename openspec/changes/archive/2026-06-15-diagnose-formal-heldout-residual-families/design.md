## Context

Current authoritative evidence lives under:

- `reports/public-sample/a100-formal-public-heldout-prediction/report.md`
- `reports/public-sample/a100-formal-public-heldout-prediction/{dev,test}/`

The formal manifest records `residual_row_count` for dev/test as `48 / 49`.
Existing alignment diagnostics already expose row-level field mismatches, but
the current repo lacks one public-safe artifact that answers the next decision
question: which residual families and field paths should be addressed first.

## Goals / Non-Goals

**Goals:**

- Produce a deterministic diagnosis from existing committed gold/prediction
  artifacts.
- Preserve count consistency against the formal held-out manifest.
- Group residuals by split, row family, task family, field path, and mismatch
  category.
- Keep strict `contract_exact_match` and strict `slot_f1` primary, with
  `slot_f1_soft` diagnostic-only.
- Recommend a bounded next phase without generating data or launching training.

**Non-Goals:**

- No new predictions, model execution, data generation, split change, SFT, DPO,
  or A100 job.
- No evaluator relaxation, semantic-equivalence scoring, prediction repair,
  prediction replacement, slot normalization, or re-scoring.
- No production, release, private-corpus, or live-browser benchmark claim.

## Decisions

1. Add a new formal-heldout diagnosis instead of reusing
   `merged_slot_value_residual_diagnosis`.
   - Rationale: the old function/report name is bound to a prior slot-value
     phase and would confuse the current formal-public evidence boundary.
   - Alternative: reuse the old report directly. Rejected because the evidence
     kind would be misleading.

2. Compute residuals from gold/prediction objects, not from alignment JSON alone.
   - Rationale: this preserves exact-contract row counts and allows field value
     summaries to be regenerated deterministically.
   - Alternative: summarize existing alignment diagnostics only. Rejected
     because it would not independently verify residual row count consistency.

3. Fail if residual row counts do not match the source manifest.
   - Rationale: a diagnosis with missing or extra residuals would be worse than
     a blocked phase.

## Risks / Trade-offs

- The report may show many residuals from `normalized_command`; this is useful
  for diagnosis but must not be reframed as semantic recovery.
- Some row ids encode family names directly; the report may aggregate by both
  source family id and contract family key to avoid over-interpreting the naming
  convention.
- This phase may point to data or policy changes, but it must not implement
  them.
