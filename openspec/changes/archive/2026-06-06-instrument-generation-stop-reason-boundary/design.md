## Context

The current trained-adapter prediction path writes `generation_trace.jsonl` rows from `_generation_trace_row(...)`. Those rows record token count, max token limit, tokenizer EOS availability/visibility, and a derived `finish_state`. The archived finish-state diagnosis established that this derived field is based on tokenizer EOS membership only and does not record the actual `generate(...)` stop reason.

This phase follows that diagnosis with a small instrumentation-only change. It should make future raw/retry traces easier to interpret without changing prediction behavior or upgrading historical A100 evidence.

## Goals / Non-Goals

**Goals:**

- Add public-safe trace fields that make the evidence basis explicit:
  - whether the generated token count hit `max_new_tokens`
  - which basis produced `finish_state`
  - what stop-boundary evidence is available from the row
  - whether an actual model/generation stop reason was recorded
- Preserve existing trace fields, sidecar path, output ordering, metrics, parsing, and retry behavior.
- Publish local evidence and a Human Brief that clearly separate instrumentation readiness from A100/model-quality claims.

**Non-Goals:**

- No A100 execution, training, checkpoint or adapter release, public full-corpus release, or model recovery claim.
- No decoding parameter change, retry prompt change, parser relaxation, output repair, prediction re-score, semantic-equivalence scoring, slot normalization, skill routing, GUI action policy learning, first-phase GRPO, or generic chat fine-tuning.
- No retrofit of historical `generation_trace.jsonl` files.

## Decisions

1. Keep `finish_state` backward compatible and add evidence-basis fields instead of renaming it.
   - Rationale: existing reports and archived evidence already consume `finish_state`; changing its meaning would create ambiguity.
   - Alternative rejected: replace `finish_state=no_eos_observed` with a new stop reason enum. That would look more precise than the available evidence supports.

2. Use conservative public-safe enums in trace rows.
   - `finish_state_basis`: `tokenizer_eos_membership` or `explicit_fixture_status`.
   - `stop_reason_evidence`: `tokenizer_eos_observed`, `max_new_tokens_reached_without_tokenizer_eos`, `not_recorded_below_max_without_tokenizer_eos`, or `fixture_no_generation`.
   - `actual_stop_reason_recorded`: `false` for the current implementation.
   - Rationale: these fields describe what the code actually observes without exposing private paths, prompts, corpus rows, or host details.

3. Treat max-token evidence as a boundary indicator, not as a full stop-reason capture.
   - Rationale: `generated_token_count >= max_new_tokens` is a useful signal, but the current code still does not capture the library's explicit stop reason object.
   - Alternative rejected: claim stop reason from token count alone. That would overstate the evidence.

## Risks / Trade-offs

- [Risk] Downstream consumers may ignore the new fields and continue reading only `finish_state`. -> Mitigation: tests, evidence, and Human Brief must call out the new boundary fields and the old field's basis.
- [Risk] Adding fields changes JSONL shape. -> Mitigation: preserve all existing keys and add only stable, public-safe fields.
- [Risk] Local instrumentation could be mistaken for model improvement. -> Mitigation: evidence and Human Brief must state that no A100 rerun, model-quality claim, decoding change, or historical trace upgrade is included.
