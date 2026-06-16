## Context

The committed form-fill boundary and field-specificity inspection for manifest `public-sample-20260616T022151Z` groups the current form-fill residual evidence into three buckets:

- `missing_confirmation_marker`: 27 cluster-row incidences and 27 residual fields, all on `normalized_command`.
- `field_specificity_or_alias_drift`: 16 cluster-row incidences and 16 residual fields, all on `slots`.
- `route_intent_leakage`: 6 cluster-row incidences and 6 residual fields across `task_type`, `route`, and `safety.reason`.

The recommended next action from that report is to define form-fill confirmation and field-specificity policy before data, prompt, training, or evaluator changes. This phase turns that recommendation into a deterministic public-safe policy artifact. It remains evidence and policy definition only.

## Goals / Non-Goals

**Goals:**

- Derive a form-fill policy artifact only from the committed form-fill boundary inspection report.
- Define policy sections for confirmation markers, field specificity or alias drift, and route or intent boundary leakage.
- Record source bucket evidence, exact split counts, field paths, source-family counts, and source count consistency.
- Record unsupported changes that this policy does not authorize, including evaluator relaxation and soft-metric promotion.
- Publish public-safe JSON, Markdown, manifest, and Human Brief artifacts.
- Add tests that enforce source manifest identity, source count consistency, policy boundaries, and leak-scan coverage.

**Non-Goals:**

- No prediction run, A100 job, SFT, DPO, GRPO, or other training.
- No dataset mutation, new candidate generation, prompt change, gold policy mutation, evaluator behavior change, or metric redefinition.
- No prediction repair, replacement, normalization, or re-score.
- No checkpoint or adapter release.
- No held-out recovery, model recovery, production readiness, private-corpus generalization, public full-corpus release, or live-browser benchmark improvement claim.

## Decisions

- Derive the policy from `form_fill_boundary_field_specificity_inspection.json`.
  - Rationale: this artifact is already public-safe, committed, and explicitly tied to the formal held-out residual-cluster evidence.
  - Alternative considered: re-read raw predictions or gold rows. Rejected because this phase should not expand the evidence surface or introduce private runtime details.

- Represent policy as structured sections plus source evidence.
  - Rationale: later data or prompt remediation needs machine-readable policy boundaries, not only prose.
  - Alternative considered: only update a Markdown report. Rejected because future phases would need to parse or duplicate free text.

- Keep policy statements prescriptive for future design but non-executing in this phase.
  - Rationale: the project needs a decision boundary before data/training, but this phase should not silently change labels, prompts, or evaluator semantics.
  - Alternative considered: immediately generate policy-aligned candidate rows. Rejected because that would combine policy definition and remediation.

- Preserve strict metric authority.
  - Rationale: prior review established that `contract_exact_match` and strict `slot_f1` remain authoritative while `slot_f1_soft` is diagnostic only.
  - Alternative considered: use policy to re-score strict residuals. Rejected because it would be evaluator relaxation without a separate approved change.

## Risks / Trade-offs

- [Risk] Policy text may be mistaken for implemented remediation. -> Mitigation: every artifact records `execution_scope` and unsupported changes, and reports state that no data, prediction, training, or evaluator change occurred.
- [Risk] `cluster_row_incidence_total` may be read as unique row count. -> Mitigation: keep the term explicit and carry source consistency fields through the policy artifact.
- [Risk] Policy examples may expose private rows. -> Mitigation: derive only from committed public-sample summary evidence and run leak scan over policy artifacts, Human Brief, and OpenSpec files.
- [Risk] The phase could block on broad domain decisions. -> Mitigation: define only the narrow observed form-fill policy surfaces and leave actual remediation for later OpenSpec phases.
