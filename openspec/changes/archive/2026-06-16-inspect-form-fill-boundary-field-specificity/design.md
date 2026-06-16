## Context

The archived residual-cluster inspection for manifest `public-sample-20260616T022151Z` ranks `form_fill / normalized_command` as the largest strict residual cluster with 27 rows and 27 field residuals. The third-ranked cluster is `form_fill / slots` with 16 rows and 16 field residuals. Earlier form-fill remediation phases added and evaluated candidates, but the current evidence still needs a narrower diagnosis of whether remaining form-fill residuals are about confirmation wording, field specificity, field alias drift, or route/task leakage.

This phase is a bridge between cluster-level diagnosis and any future remediation. It must not mutate the dataset, run prediction, run training, or soften evaluation semantics.

## Goals / Non-Goals

**Goals:**

- Inspect only the form-fill residual clusters from the committed residual-cluster report.
- Classify representative and counted form-fill residuals into deterministic diagnostic buckets.
- Preserve split/source-family counts and source examples so later phases can decide whether data, prompt, policy, or evaluator work is justified.
- Publish public-safe JSON, Markdown, manifest, and Human Brief artifacts.
- Add tests that enforce source manifest identity, bucket counts, analysis-only boundaries, and leak-scan coverage.

**Non-Goals:**

- No prediction run, A100 job, SFT, DPO, GRPO, or other training.
- No dataset mutation or new candidate generation.
- No prompt, gold policy, evaluator, metric, schema, or decoder behavior change.
- No prediction repair, replacement, normalization, or re-score.
- No checkpoint or adapter release.
- No held-out recovery, model recovery, production readiness, private-corpus generalization, public full-corpus release, or live-browser benchmark improvement claim.

## Decisions

- Derive the inspection from `formal_heldout_residual_cluster_inspection.json`.
  - Rationale: the cluster report is already public-safe, committed, and tied to the current formal held-out manifest.
  - Alternative considered: re-read raw predictions or alignment files. Rejected because this phase should not expand the evidence surface or risk copying private runtime details.

- Use deterministic bucket labels rather than LLM-generated labels.
  - Rationale: bucket assignments must be stable in tests and safe to regenerate.
  - Alternative considered: use an LLM to summarize examples. Rejected because it would add non-determinism and could overstate root cause.

- Keep buckets diagnostic rather than prescriptive.
  - Rationale: a bucket such as `missing_confirmation_marker` or `field_alias_drift` can inform a later proposal, but it must not authorize immediate data or training changes.
  - Alternative considered: automatically select and implement a remediation. Rejected because the prior held-out run did not prove recovery and safety-sensitive clusters remain nearby.

- Report both row counts and field counts.
  - Rationale: form-fill normalized-command and slot clusters overlap in rows but represent different failure surfaces; future phases need both views.
  - Alternative considered: rank by rows only. Rejected because it hides multi-field residual density.

## Risks / Trade-offs

- [Risk] Diagnostic buckets may look like root-cause proof. -> Mitigation: label them as inspection buckets, include source examples, and preserve strict metric boundaries.
- [Risk] The analysis may encourage another broad data expansion. -> Mitigation: output only candidate next actions and require a separate OpenSpec phase for data/training changes.
- [Risk] Reported Chinese examples could expose raw private rows. -> Mitigation: derive from committed public-sample residual summaries and run leak scan over report, Human Brief, and OpenSpec archive.
- [Risk] The phase may duplicate earlier form-fill remediation work. -> Mitigation: explicitly compare against the current residual-cluster evidence and avoid candidate generation.
