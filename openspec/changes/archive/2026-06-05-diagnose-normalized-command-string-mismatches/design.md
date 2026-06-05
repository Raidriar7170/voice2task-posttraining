## Context

The archived `diagnose-confirmation-rerun-row-mismatches` phase produced a public-safe row-level diagnosis for the real private-adapter confirmation-required train-split rerun. It reported `normalized_command=3` in `field_mismatch_counts`, while the strict final metrics remained unchanged: `json_valid_rate=2/3`, `contract_exact_match=0.0`, `task_type_accuracy=1/3`, `route_accuracy=1/3`, and `confirmation_accuracy=2/3`.

The three rows have different surrounding failure contexts:

- `seed-search-weather`: `normalized_command` differs while the same row remains schema-invalid because `confirmation_required` is missing.
- `seed-search-weather-aug-1`: `normalized_command` differs while task type, route, and safety reason also differ.
- `seed-search-weather-aug-2`: `normalized_command` is the only field mismatch, so this row is the strict string-only exact-match case.

This phase explains those string-level differences without deciding that any pair is semantically equivalent.

## Goals / Non-Goals

**Goals:**

- Derive a normalized-command string-mismatch diagnosis from committed public-safe row-mismatch evidence.
- Count total `normalized_command` mismatches, string-only mismatches, schema-failure co-occurrences, and semantic task/route/safety co-occurrences.
- Preserve source prediction status and strict metrics.
- Keep reports public-safe and claim-bounded.
- Generate focused tests, leak scans, Human Brief HTML, Reviewer review, OpenSpec archive, and guarded commit.

**Non-Goals:**

- No A100 execution.
- No SFT, DPO, GRPO, training, prediction rerun, checkpoint, or adapter creation.
- No prompt, decoder, parser, schema retry, schema, or evaluator metric changes.
- No semantic-equivalence scoring for `搜索/查询` or `明天的天气/明天天气`.
- No normalization, repair, coercion, replacement, or re-scoring of predictions.
- No dev/test held-out generalization, release, production-readiness, public full-corpus, model-quality, or live-browser benchmark claim.

## Decisions

1. **Use the previous row-mismatch evidence as the primary input.**
   - Rationale: it already preserves source prediction status, row-level field mismatches, source artifact links, and strict metrics.
   - Alternative considered: recompute from train gold and predictions. Rejected for this phase because the prior evidence is already the committed public-safe row-level authority.

2. **Classify by surrounding failure context instead of semantic meaning.**
   - Rationale: the safe question is where the string mismatch appears, not whether two Chinese strings are equivalent.
   - Alternative considered: add a normalization/semantic-match rule. Rejected because that would change evaluator interpretation and needs a separate user decision.

3. **Keep the implementation as a small derived diagnostic.**
   - Rationale: a pure helper plus Markdown/JSON report writer keeps the phase testable without expanding CLI or training surfaces.
   - Alternative considered: add a CLI subcommand. Rejected as unnecessary for this one-off evidence pack.

## Risks / Trade-offs

- [Risk] The report accidentally implies `normalized_command` semantic equivalence. -> Mitigation: explicitly state that no normalization or semantic-equivalence scoring is applied.
- [Risk] The evidence sounds like model recovery. -> Mitigation: preserve strict metrics and repeat non-claim boundaries.
- [Risk] The phase duplicates prior row-mismatch evidence. -> Mitigation: make it a narrow drill-down that links back to the prior evidence and only adds normalized-command context counts.
- [Risk] Public artifacts leak private runtime details through inherited metadata. -> Mitigation: use committed sanitized artifacts only and run leak scans over evidence, Human Briefs, archived OpenSpec, and synced specs.
