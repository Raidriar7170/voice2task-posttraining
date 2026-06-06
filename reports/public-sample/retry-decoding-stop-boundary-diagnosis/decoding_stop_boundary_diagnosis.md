# Retry decoding stop-boundary diagnosis

Conclusion: raw generation reached EOS before the 256 token limit, but retry generation finish/stop evidence is not recorded, so this phase cannot claim a retry EOS or stop-token root cause.

## Observed facts

- Source phase: `reports/public-sample/a100-schema-retry-wrapper-boundary-rerun`.
- Strict final JSON valid rate remains `0`; contract exact match remains `0`.
- Raw generation trace exists for `3/3` rows with finish state counts `{"eos_observed":3}`.
- Raw generated token counts are `52-54`, below `max_new_tokens=256`; raw max-token truncation is unlikely.
- Retry attempts still parse as `{"json_fragment_object":3}` and remain prose/Markdown-wrapped for `3/3` rows.
- Retry text visibly contains Markdown fences for `3/3`, forbidden prefaces for `2/3`, trailing analysis for `3/3`, and `task_type=search` content for `3/3`.

## Evidence boundary

- Current `generation_trace.jsonl` records raw attempt token and finish state only.
- It does not record retry attempt generated token count, EOS visibility, finish state, stop reason, or token limit hit status.
- Therefore raw EOS evidence must not be reused as retry EOS evidence.

## Interpretation

- This is local evidence-only analysis from already committed public-safe sidecars.
- The strongest current hypothesis is instruction-following/explanatory style during retry, not parser relaxation or evaluator semantics.
- Recommended next step: instrument retry generation traces before changing decoding behavior or running another A100 phase.

## Non-claims

No A100 execution, private prediction rerun, training, decoding change, parser relaxation, evaluator metric change, output repair, re-score, slot normalization, checkpoint release, adapter release, model recovery claim, model-quality claim, or live-browser benchmark improvement claim is made.
