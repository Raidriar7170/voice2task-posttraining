## Context

The latest A100 rerun preserved two useful evidence streams:

- `generation_trace.jsonl`: raw attempt generation trace only, including `finish_state=eos_observed`, `eos_token_seen=true`, `generated_token_count=52-54`, and `max_new_tokens=256`.
- `raw_decoded_summary.jsonl`: raw and retry decoded text summaries, including retry parse status and sanitized prefixes/suffixes.

The trace design currently does not record retry attempt `generated_token_count`, EOS, finish state, or stop reason. Therefore a decoding/stop-boundary fix would be premature without first documenting the evidence gap.

## Diagnosis Plan

Use existing public-safe sidecars only:

- Confirm raw attempts are not max-token truncation symptoms.
- Confirm retry attempts still violate wrapper-boundary constraints.
- Record which retry stop/boundary evidence is missing.
- Recommend a next phase only as a user-confirmed behavior change: instrument retry generation traces or test decoding stop/boundary parameters locally before any A100 rerun.

## Risks

- The diagnosis may be mistaken if treated as model-quality evidence. It must remain evidence-gap and hypothesis documentation.
- Future instrumentation of retry traces would change sidecar schema and must be scoped separately.
- Future stop-boundary decoding changes could alter model behavior and success criteria, so they require user confirmation.
