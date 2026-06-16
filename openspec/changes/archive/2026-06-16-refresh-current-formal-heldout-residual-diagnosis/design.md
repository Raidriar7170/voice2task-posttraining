## Context

The latest project closeout uses
`reports/public-sample/a100-formal-public-heldout-prediction-after-a100-recovery/`
as the current public-facing truth surface. The committed residual-family
diagnosis and remediation target-selection artifacts already provide the right
diagnostic shape, but their source evidence still points to the earlier formal
held-out manifest. That is enough to confuse readers and future agents about
which manifest is current.

## Goals / Non-Goals

**Goals:**

- Regenerate formal residual-family diagnosis from the current A100 recovery
  evidence pack.
- Regenerate formal remediation target-selection from that refreshed diagnosis.
- Regenerate formal residual-cluster inspection from that refreshed diagnosis.
- Refresh downstream confirmation-marker coverage source evidence so it reads
  the current residual cluster while preserving the older policy/remediation
  provenance that produced already-materialized candidates.
- Add tests that make the current manifest id and evidence path explicit.
- Keep the result public-safe and diagnosis-only.

**Non-Goals:**

- No SFT, DPO, A100 prediction run, data generation, public sample mutation, or
  evaluator metric change.
- No change to strict `contract_exact_match`, strict `slot_f1`, or
  `slot_f1_soft` semantics.
- No new checkpoint, adapter, private-corpus, or live-browser claim.
- No automatic jump into form-fill, clarify, or blocked-payment remediation.
- No rewrite of already-materialized confirmation-marker extension candidate
  rows or formal public sample provenance.

## Decisions

1. **Refresh existing generic report locations instead of adding a new
   timestamped report path.**

   Rationale: the existing paths are already the project-level "current formal
   residual diagnosis" and "current formal target selection" surfaces. Updating
   them avoids two competing current reports.

   Alternative considered: create
   `formal-heldout-residual-family-diagnosis-after-a100-recovery/`. That would
   preserve history but would also make the public truth surface harder to find.

2. **Use the existing CLI and report writers where possible.**

   Rationale: the residual diagnosis and target selection logic already has
   public-safe boundaries and tests. The phase should validate current evidence
   binding, not invent a second diagnostic implementation.

3. **Treat any target recommendation as a decision artifact, not permission to
   train.**

   Rationale: the latest metrics are still partial signal. A selected target may
   justify a later OpenSpec proposal, but this phase only refreshes evidence and
   documents the next decision point.

## Risks / Trade-offs

- **Risk: refreshed metrics look numerically identical to prior metrics.**
  Mitigation: the report must still record the newer manifest id and comparison
  boundary so "same numbers" is not mistaken for stale evidence.
- **Risk: target selection chooses a previously discussed target.** Mitigation:
  the output must preserve the no-auto-remediation boundary and recommend a
  separate bounded proposal before data/training/metric changes.
- **Risk: a direct downstream report remains bound to stale diagnosis evidence.**
  Mitigation: refresh and test residual-cluster inspection alongside diagnosis
  and target selection.
- **Risk: evidence refresh rewrites historical candidate provenance.**
  Mitigation: refresh only the coverage artifact's current residual evidence
  pointer; preserve legacy policy and materialized candidate source manifest
  lineage.
- **Risk: public artifacts leak private runtime context.** Mitigation: run the
  existing leak scan over the refreshed reports and Human Brief before commit.
