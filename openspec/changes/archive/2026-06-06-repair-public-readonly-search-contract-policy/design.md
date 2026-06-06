# Design

## Context

The prior row-level diagnosis under `reports/public-sample/a100-normalized-rerun-row-mismatch-diagnosis/` found three distinct residual families:

- `schema_missing_confirmation_required`
- `schema_invalid_task_type_enum`
- `schema_valid_task_route_safety_slot_mismatch`

Existing prompt repairs already expose route ontology, required fields, a canonical one-shot, and normalized-command canonicalization. The remaining local gap is that public-readonly search/weather requests are not presented as one cohesive field policy: task type, route, safety reason, confirmation behavior, and query slots should be visible together.

## Approach

1. Add a compact `PUBLIC_READONLY_SEARCH_CONTRACT_POLICY` prompt fragment to the shared system prompt.
2. Update `prompt_constraint_summary()` with explicit flags for:
   - public-readonly search policy visibility,
   - public-readonly safety reason visibility,
   - search query slot guidance,
   - task type not being reused as route enum values.
3. Add focused tests that:
   - prove training and prediction prompts include the policy;
   - prove prediction prompts do not include row-specific gold-only tokens;
   - prove prompt constraint metadata surfaces the new policy flags.
4. Publish a local evidence pack derived from current prompt metadata and prior public row-mismatch evidence.
5. Keep all claims bounded: this phase is local prompt/policy hardening only, not model recovery or a private runtime result.

## Decisions

1. **Use prompt policy rather than schema aliasing.**
   - Rationale: accepting `task_type="search_web"` as an alias would hide the exact schema failure. The contract enum remains authoritative.
2. **Use non-row-specific examples.**
   - Rationale: prediction prompts must not include the current row's gold target contract. Examples should teach field policy without leaking labels.
3. **Do not modify evaluator metrics or slot scoring.**
   - Rationale: the strict failure evidence should remain comparable to earlier phases. This phase only makes the intended contract policy visible.

## Risks And Mitigations

- Risk: A reader treats the policy evidence as A100 recovery.
  - Mitigation: manifest, report, Human Brief, and tests require local-only non-claim boundaries.
- Risk: Prompt text becomes too verbose.
  - Mitigation: add one compact policy fragment that ties together fields already present elsewhere.
- Risk: The `slots.query` guidance is mistaken for semantic equivalence.
  - Mitigation: evidence states no slot normalization, no semantic-equivalence scoring, and no re-score.
