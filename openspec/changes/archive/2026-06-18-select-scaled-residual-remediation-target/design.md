# Design: Scaled Residual Remediation Target Selection

## Context

The current public-facing evidence boundary is the scaled formal public sample
manifest `public-sample-20260617T152259Z` evaluated with the existing
current-123 adapter. The previous phase produced a residual-cluster inspection
under
`reports/public-sample/scaled-current-123-adapter-residual-cluster-inspection/`.

That inspection is analysis-only and reports 29 clusters, 321 residual rows,
and 540 residual fields. The top strict residual cluster is
`clarify|clarify|ambiguous_request|confirm:true|slots:ambiguity` on `slots`
with 78 residual rows. The next clusters include safety-sensitive
blocked-payment slots and canonicalization-oriented search/navigate/form-fill
slot residuals.

## Goals / Non-Goals

**Goals:**

- Produce a public-safe target-selection evidence pack from the committed
  cluster-inspection JSON.
- Select one first remediation target and record the ranked alternatives.
- Preserve the strict comparison boundary and diagnostic-only status of
  `slot_f1_soft`.
- Make the next recommended phase explicit without performing it.

**Non-Goals:**

- No A100 execution, prediction rerun, SFT/DPO/GRPO training, data
  materialization, prompt change, evaluator relaxation, semantic-equivalence
  scoring, slot normalization, prediction repair, or checkpoint/adapter release.
- No claim that selecting a target improves model quality.
- No direct old/new metric comparison across mismatched manifests.

## Decisions

1. **Select from cluster inspection, not raw predictions.**

   The selector reads
   `formal_heldout_residual_cluster_inspection.json` and does not read raw
   predictions or private rows. The previous phase already sanitized and
   clustered the residual evidence; this phase should not reopen private data
   surfaces.

2. **Prefer the largest non-safety slots cluster as the first target.**

   The top cluster is `clarify/slots` with 78 residual rows and 78 residual
   fields. It is larger than `blocked/slots`, `search/slots`, and
   `form_fill/slots`, and it is a route/intent boundary issue rather than a
   safety-policy repair. The first recommended next phase should therefore be a
   bounded clarify slot-boundary candidate design.

3. **Defer blocked-payment residuals to a dedicated safety phase.**

   `blocked/slots` is high-ranked, but it touches unsafe-payment refusal
   semantics. Mixing it into a generic data expansion phase risks obscuring
   safety precision/recall boundaries. The selector should record it as a
   deferred safety target rather than picking it first.

4. **Keep canonicalization residuals explicit but not first.**

   Search, navigate, extract, and form-fill slot residuals remain important,
   but after the scaled inspection they are not the largest cluster. They should
   be candidates for later canonicalization or family-specific phases.

## Risks / Trade-offs

- **Risk:** Selecting `clarify/slots` from aggregate cluster size could miss a
  higher-severity safety issue.
  **Mitigation:** Defer blocked-payment residuals explicitly to a dedicated
  safety phase and do not claim they are solved.

- **Risk:** The target-selection report could be mistaken for data expansion or
  model recovery.
  **Mitigation:** Carry the same claim-boundary flags used by the previous
  evidence packs and test them.

- **Risk:** Future readers may compare this evidence directly to older
  manifests.
  **Mitigation:** Record the source manifest and comparison boundary in JSON,
  Markdown, `CONTEXT.md`, and `reports/final_status.md`.
