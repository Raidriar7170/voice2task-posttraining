## Context

The latest A100 search-query slot-policy rerun produced compact `slots.query` content inside the decoded fragments, but the final predictions were still Markdown-wrapped and strict schema-valid output remained `0/3`. The current public-safe evidence pack already captures the rerun outputs, metrics, schema guard summary, and a first-pass diagnosis, but it does not yet separate the wrapper symptom from the still-unknown wrapper origin in a dedicated local diagnosis artifact.

This change is local and evidence-only. It uses existing sanitized public artifacts and does not launch another A100 rerun, change decoding, or reinterpret the strict metrics.

## Goals / Non-Goals

**Goals:**
- Publish a public-safe diagnosis pack for the search-query slot wrapper boundary.
- Separate observed facts, wrapper symptoms, and evidence gaps so the phase does not overclaim model recovery.
- Preserve strict metrics and raw evidence as source material.
- Add a concise Chinese Human Brief and focused tests for the diagnosis pack.

**Non-Goals:**
- No A100 execution, training, fine-tuning, DPO, GRPO, or new prediction rerun.
- No parser relaxation, slot normalization, decoding change, metric relaxation, prediction repair, prediction re-score, or semantic-equivalence scoring.
- No model-quality, held-out generalization, production-readiness, or live-browser benchmark claim.

## Decisions

1. Use the existing public-safe search-query slot-policy rerun evidence as the sole source input.
   - Rationale: the diagnosis question is about boundary interpretation, not new model behavior.
   - Alternative considered: launch another A100 rerun to probe the wrapper. Rejected because it changes the scope and would blur whether the boundary moved.

2. Keep the diagnosis artifact separate from the source rerun evidence.
   - Rationale: the diagnosis should summarize observed facts and gaps without mutating the original predictions or metrics.
   - Alternative considered: fold the diagnosis into the rerun report only. Rejected because the rerun evidence pack already exists and the new phase needs its own public-safe record.

3. Treat wrapper origin as unknown unless current evidence proves otherwise.
   - Rationale: the observed Markdown fence is enough to explain strict failure, but not enough to assign blame to the prompt, template, decoder, or post-processing.
   - Alternative considered: infer a specific wrapper source from the output shape. Rejected because that would overclaim beyond the available evidence.

4. Modify `contract-evaluation` and `supervised-contract-tuning` only.
   - Rationale: the phase is about evidence boundary and future behavior boundary, not a new product capability.
   - Alternative considered: add a new capability spec. Rejected because the existing specs already cover the contract and tuning boundary that this diagnosis is constraining.

## Risks / Trade-offs

- [Risk] The diagnosis may still be ambiguous about where the wrapper originates.
  - Mitigation: state the unknown explicitly and recommend any future instrumentation as a separate user-confirmed phase.

- [Risk] The phase could be misread as proof of model improvement because compact query content is visible.
  - Mitigation: preserve strict metrics, emphasize `0/3` schema-valid output, and keep claims boundary explicit in the report and Human Brief.

- [Risk] Future instrumentation or decoding changes could require schema or evidence-shape updates.
  - Mitigation: scope those changes as a later OpenSpec phase rather than smuggling them into this diagnosis.
