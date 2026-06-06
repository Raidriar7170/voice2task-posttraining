## Context

The previous A100 public-readonly search policy rerun produced real private-adapter train-split evidence. It showed the local prompt policy was visible in metadata and raw text, but all three final predictions remained strict schema-invalid. The field-level diagnosis recorded three consistent symptoms:

- raw outputs emitted malformed top-level JSON where some fields appeared outside the root object;
- retry outputs contained prose and Markdown wrappers that the strict retry parser correctly rejected;
- raw `task_type` remained `search_web`, which is a route enum value, not the Browser Task Contract task type `search`.

This phase applies a small local policy repair. It does not claim that the private adapter improves until a later separately authorized A100 rerun observes that behavior.

## Goals / Non-Goals

**Goals:**

- Make the single-root-object boundary visible in both normal prediction prompts and retry prompts.
- Make public-readonly search task-type guidance explicit and compact: `task_type="search"` and never `search_web`.
- Keep prompt length within the existing `max_seq_length=2048` local fake-tokenizer guard.
- Generate public-safe evidence and Human Briefs that describe the local repair and its limitations.

**Non-Goals:**

- No A100 execution, training, private prediction rerun, checkpoint release, adapter release, or deployment.
- No repair, coercion, normalization, semantic-equivalence scoring, metric relaxation, or re-score of historical predictions.
- No claim of held-out generalization, production readiness, model quality improvement, or live-browser benchmark improvement.

## Decisions

1. **Patch prompt/retry policy rather than parser semantics.**
   - Rationale: the strict parser already rejects malformed JSON and prose wrappers; changing parser semantics would hide the failure mode.
   - Alternative considered: parse JSON fragments from retry text. Rejected because prior evidence explicitly needs invalid outputs to remain invalid.

2. **Keep the policy compact.**
   - Rationale: the shared SFT prompt is near the runtime sequence-length budget; adding verbose examples would risk local training-record failures.
   - Alternative considered: add long natural-language examples. Rejected in favor of short rules and one canonical skeleton.

3. **Produce local evidence only.**
   - Rationale: this phase changes prompt text; the next A100 question is separate and requires explicit A100 authorization.
   - Alternative considered: immediately rerun A100. Rejected because it would cross the private-infrastructure boundary and hide whether the local policy was properly validated.

## Risks / Trade-offs

- [Risk] More prompt text exceeds the fake-tokenizer `max_seq_length=2048` guard. -> Mitigation: compress wording and rerun formatting/training tests.
- [Risk] The next A100 rerun still emits malformed output. -> Mitigation: report this phase as preparation/local hardening only and stop before overclaiming.
- [Risk] Reports imply historical A100 predictions were fixed. -> Mitigation: evidence says no prediction repair, no re-score, and no A100 execution in this phase.
