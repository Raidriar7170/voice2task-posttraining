## Context

The prior merged slot-value held-out evidence reports:

- train: `contract_exact_match=1.0`, residual rows `0`
- dev: `contract_exact_match=0.5`, residual rows `3`, strict `slot_f1=0.5`, soft `slot_f1_soft=1.0`
- test: `contract_exact_match=0.8333333333333334`, residual rows `1`, strict `slot_f1=1.0`, soft `slot_f1_soft=1.0`

The committed public bundle intentionally contains aggregate metrics and sanitized prediction metadata, not raw prediction rows. Row-level diagnosis therefore needs to consume ignored/private prediction artifacts or an A100-derived sanitized residual summary, then commit only the public-safe derived diagnosis.

## Goals / Non-Goals

**Goals:**

- Identify the remaining dev/test strict residuals by split, row id, task family, field path, and mismatch category.
- Make the strict-vs-soft boundary explicit, especially where soft slot matching is perfect but strict exact match still fails.
- Publish a public-safe machine-readable diagnosis, Markdown report, leak scan result, and Human Brief.
- Recommend the next bounded decision from evidence.

**Non-Goals:**

- No new SFT/DPO/GRPO training, prediction rerun, or model download.
- No evaluator relaxation, semantic-equivalence scoring, slot normalization, prediction repair, prediction replacement, or re-score.
- No formal public sample merge or new data materialization.
- No generic chat fine-tuning, skill routing, GUI action policy learning, checkpoint release, adapter release, production-readiness claim, held-out recovery claim, public full-corpus release, or live-browser benchmark claim.

## Decisions

1. **Use diagnosis-only derived artifacts.**
   - Rationale: private A100 predictions are useful evidence, but raw prediction sidecars can contain private runtime details. The committed output should include only row ids, public gold/prediction field summaries, mismatch categories, aggregate counts, and claim boundaries.
   - Alternative considered: commit split `predictions.jsonl` directly. Rejected because this phase only needs residual summaries and should minimize public surface.

2. **Classify mismatches at field-path level.**
   - Rationale: aggregate residual counts do not distinguish slot-value strict drift from normalized command or other contract fields. Field-path categories make the next stage evidence-based.
   - Alternative considered: only report row ids. Rejected because it would not tell us whether data generalization, canonical wording, or prompt policy is the next lever.

3. **Preserve strict metric authority.**
   - Rationale: `slot_f1_soft=1.0` is an internal diagnostic, not the primary evaluator. The report must keep `contract_exact_match` and strict `slot_f1` authoritative.
   - Alternative considered: treat soft slot F1 as recovery. Rejected because it would weaken the evidence boundary.

4. **Stop after recommendation if the next step changes data/training policy.**
   - Rationale: deciding to broaden data, merge examples, canonicalize targets, or train again changes scope and should be a new confirmed phase.

## Risks / Trade-offs

- **Risk: private paths leak through copied sidecars.** -> Mitigation: process ignored/private inputs into sanitized reports and run leak scan before commit.
- **Risk: diagnosis is mistaken for model improvement.** -> Mitigation: report no training/prediction change and keep strict metrics unchanged.
- **Risk: raw predictions are unavailable.** -> Mitigation: publish a blocked evidence note that aggregate artifacts are insufficient for row-level diagnosis, rather than inventing causes.
- **Risk: next-step pressure causes scope creep.** -> Mitigation: produce only a recommendation and stop before data/training/evaluator policy changes.
