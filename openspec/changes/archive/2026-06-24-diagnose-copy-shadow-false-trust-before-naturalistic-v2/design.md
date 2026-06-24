## Context

The archived `recover-and-run-frozen-adapter-challenge-evaluation` phase ran the frozen template-disjoint challenge through the canonical prediction hook and selected `CHALLENGE_V1_HOOK_UNSAFE_OR_INVALID`. The evidence showed no prediction mutation, no runtime decision change, no V1 metric delta, no action trusted provenance, and no normalized trusted provenance. It also showed source-attested-but-gold-mismatch cases, including source-absent substitution, normalization collision, and partial-span/overlong-span risks.

The next phase must not rerun prediction or change any frozen artifacts. It only re-audits committed artifacts to separate technical source attestation from semantic correctness, classify mismatch mechanisms, and propose a bounded next step.

## Goals / Non-Goals

**Goals:**

- Verify the committed input boundary before diagnosis.
- Recompute all source-attested-but-gold-mismatch cases from challenge rows, predictions, online sidecars, and offline audits.
- Rename the semantic surface from `trusted_provenance` to `source_attested_exact` in new artifacts while preserving old artifacts unchanged.
- Detect normalized-equivalent collisions deterministically and downgrade those events during re-audit.
- Produce a public-safe case ledger, per-scope risk review, collision audit, sidecar v2 semantics note, summary, and recommended next change.
- Update README/CONTEXT/evidence index and add a concise Chinese Human Brief.

**Non-Goals:**

- No A100, SSH, GPU job, model training, prediction rerun, prompt change, decoding change, prediction repair, or challenge v2 creation.
- No modification to challenge v1 rows, gold, condition tags, frozen policy v1, historical predictions, online sidecars, offline evaluation audits, BrowserTaskContract V1, ContractCoreV2, evaluator logic, runtime execution policy, or training data.
- No LLM judge, embedding similarity, semantic-equivalence scoring, runtime enforcement, action enablement, normalized trusted provenance, slot accuracy claim, model improvement claim, executable quality claim, or production/safety readiness claim.

## Decisions

1. **Implement diagnosis as an offline report generator.**
   - Rationale: The phase must not affect the canonical hook, runtime, predictions, or evaluator.
   - Alternative rejected: Updating historical sidecars in place would erase the provenance of the previous evaluation and violate the bounded phase.

2. **Use a compatibility mapping instead of renaming historical fields.**
   - New artifacts map `trusted_provenance=true` and `VERIFIED_EXACT_UNIQUE` to `source_attested_exact=true`.
   - `trusted_provenance` remains a deprecated alias in historical artifacts only.
   - Rationale: This keeps old evidence reproducible while making new semantics explicit.

3. **Treat normalized-equivalent collision detection as a downgrade audit.**
   - The detector examines raw-exact source-attested events and checks whether normalized-equivalent candidate spans are ambiguous.
   - Collision cases become `AMBIGUOUS_NORMALIZATION_COLLISION` in new diagnosis artifacts only.
   - Rationale: This blocks a known false-trust path without enabling normalized trusted provenance.

4. **Classify semantic mismatches with explicit mechanism taxonomy.**
   - Each source-attested-but-gold-mismatch event receives one primary mechanism and optional secondary mechanisms.
   - Technical span attestation failures are separated from semantic selection errors and policy scope errors.
   - Rationale: Source provenance can be valid even when model semantic choice is wrong.

5. **Evaluate scope suitability without changing policy v1.**
   - The report proposes policy-v2 status per enabled scope: `OBSERVE_ENABLED`, `OBSERVE_LIMITED`, `PROPOSE_DISABLE`, or `INSUFFICIENT_EVIDENCE`.
   - Rationale: The same challenge cannot be used to tune policy and then claim improved evaluation.

## Risks / Trade-offs

- **Risk: Mechanism classification can overstate certainty.** -> Use `UNCLASSIFIED_SEMANTIC_MISMATCH` when deterministic rules cannot safely classify a case.
- **Risk: Normalization rules can introduce new ambiguity.** -> Keep normalization bounded, deterministic, auditable, and candidate-only.
- **Risk: Case ledger can expose too much text.** -> Use public-safe challenge inputs only, sanitize outputs, and run leak scan.
- **Risk: Report consumers may read source attestation as execution readiness.** -> Set `execution_eligible=false` everywhere and document that online sidecars do not infer semantic correctness.
- **Risk: The phase may drift into policy v2 or challenge v2.** -> Emit only one next-change recommendation and stop after validation.
