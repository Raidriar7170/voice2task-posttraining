## Context

The frozen copy-shadow challenge v1 and Policy V1 artifacts already show that
source attestation is source-only evidence. The previous false-trust diagnosis
also showed that the per-scope recommendation surface must be recomputed from
post-hardening evidence instead of from hard-coded scope names. This change is a
review-only design step before any Policy V2 freeze, naturalistic challenge,
training, runtime hook, or action enablement work.

The design must consume only committed public-safe artifacts: challenge v1,
adapter evaluation reports, false-trust diagnosis reports, prediction sidecars,
evaluation audits, Policy V1, and current truth surfaces. It must fail closed
when those inputs drift or contradict each other.

## Goals / Non-Goals

**Goals:**

- Add a deterministic gate engine for copy-shadow scope decisions.
- Split fixture/gold ambiguity from canonical-string mismatch in the diagnosis
  interpretation layer.
- Record fixture-guided mismatch attribution explicitly per ledger row.
- Emit compact post-hardening metrics, scope decisions, taxonomy migration
  evidence, and a proposed inactive Policy V2 JSON.
- Preserve Policy V1, challenge v1, predictions, sidecars, evaluator behavior,
  prompts, decoding, model weights, training data, and runtime loading.

**Non-Goals:**

- No SFT, DPO, GRPO, A100, SSH, GPU, training, prediction reruns, prompt
  changes, decoding changes, challenge/gold/tag edits, evaluator changes, or
  semantic LLM/embedding scoring.
- No runtime enforcement, hook loading, action trust, normalized trust, policy
  generalization, production-readiness claim, safety-readiness claim, or
  naturalistic challenge v2 work.
- No overwrite of Policy V1 or raw historical artifacts.

## Decisions

1. Deterministic inputs and fail-closed validation

   The design engine will validate challenge hash, Policy V1 id/version/hash,
   adapter identity evidence, prediction/sidecar/audit alignment, collision
   downgrade evidence, V1 zero-delta evidence, and source-only sidecar
   invariants before emitting Policy V2 design artifacts. If validation fails,
   the engine writes a blocked artifact and does not emit a proposed policy.

   Alternative considered: run the gate engine on best-effort inputs. Rejected
   because policy-review artifacts would become a second source of truth.

2. Metrics are computed per scope, not hard-coded by slot name

   Scope decisions will be keyed by the input scope identifier. Gate status
   comes from counts, Wilson 95% intervals, high-risk mismatch rate, adapter
   balance, evidence sufficiency, technical false accepts, and policy
   violations. Special scope semantics are represented as deterministic
   evidence flags and optional downward review overrides, not as unconditional
   slot-name branches.

   Alternative considered: preserve the earlier per-scope recommendation table.
   Rejected because the previous table could hide sample-size and adapter-bias
   limits.

3. Taxonomy split is an interpretation migration

   Historical `CHALLENGE_FIXTURE_OR_GOLD_AMBIGUITY` rows will be migrated into
   `TRUE_GOLD_OR_FIXTURE_AMBIGUITY` or `CANONICAL_STRING_MISMATCH` using
   fixture tags and deterministic value-relation checks. The report must make
   this attribution `fixture_guided`; it is not independent semantic proof.

   Alternative considered: keep the old taxonomy and document the ambiguity.
   Rejected because Policy V2 gates need to separate low-risk canonical-string
   mismatches from true fixture/gold uncertainty.

4. Gate statuses are reproducible and downward-only review is explicit

   The engine will compute one original gate status from the configured order:
   technical/policy failure, evidence insufficiency, disable, enabled, limited,
   otherwise candidate-only. Review overrides may only move a scope downward and
   must record reason, evidence reference, and reviewer requirement.

   Alternative considered: allow manual final status assignment. Rejected
   because it would reintroduce untraceable policy judgment.

5. Proposed Policy V2 remains inactive

   `configs/copy-backed-scope-policy-v2.proposed.json` will declare
   `status=proposal`, `active=false`, `runtime_loaded=false`, and
   `enforcement_enabled=false`. No runtime code will load it.

   Alternative considered: add runtime loader scaffolding behind a flag.
   Rejected because this phase is design/review only.

## Risks / Trade-offs

- Small or imbalanced samples may produce conservative statuses -> report
  `INSUFFICIENT_EVIDENCE` or `CANDIDATE_ONLY` instead of upgrading scopes.
- Fixture-guided attribution is useful for diagnosis but weak as independent
  evidence -> every migrated ledger row records attribution mode/source and
  manual-review status.
- Wilson intervals make gates stricter than raw accuracy -> gate reports include
  both raw rates and interval bounds.
- Public-safe reports may omit raw examples -> evidence references link to
  committed sanitized artifacts only.

## Migration Plan

1. Add tests for gate logic, taxonomy migration, proposed-policy invariants, and
   input-boundary preservation.
2. Add the design module and report script.
3. Regenerate only the bounded diagnosis interpretation artifacts and Policy V2
   design reports.
4. Run focused and full validation.
5. Leave Policy V2 as an inactive proposal for review.

Rollback is deleting this change's new reports, docs, proposed policy, and code.
Policy V1 and frozen challenge artifacts are not modified by this phase.

## Open Questions

- Whether a later review phase freezes Policy V2 as a runtime-visible policy is
  intentionally outside this change.
- Whether additional independent observe-only evidence should be collected
  before Policy V2 freeze depends on the deterministic gate outcome.
