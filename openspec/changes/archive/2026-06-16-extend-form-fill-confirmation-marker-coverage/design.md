## Context

The archived confirmation-marker coverage assessment established a concrete gap: the current `missing_confirmation_marker` policy surface has 27 normalized-command residual incidences across 12 source families, while existing legacy remediation covers only 3 field labels (`手机号`, `收货地址`, `发票抬头`). The formal held-out residual cluster still exists, so the project needs a candidate-design phase before any materialization, merge, prompt change, or training.

This phase works only from committed public-safe artifacts:

- `reports/public-sample/form-fill-confirmation-marker-coverage/form_fill_confirmation_marker_coverage.json`
- `reports/public-sample/form-fill-confirmation-field-policy/form_fill_confirmation_field_policy.json`
- existing form-fill remediation case-design/materialization/merge artifacts
- formal held-out residual cluster inspection artifacts

## Goals / Non-Goals

**Goals:**

- Design a bounded extension set of confirmation-marker candidate cases from the observed source-family coverage gap.
- Preserve provenance from the coverage assessment and policy artifact.
- Report represented source families, represented field labels, uncovered source families, candidate count, and source count consistency.
- Emit public-safe JSON, Markdown, manifest, and Human Brief artifacts.
- Add tests that prevent confusing candidate design with data mutation or held-out recovery.

**Non-Goals:**

- No seed trace, public sample, SFT, DPO, held-out gold, or candidate-row mutation.
- No prompt, gold policy, evaluator, prediction, checkpoint, adapter, or training change.
- No A100 job, SFT, DPO, GRPO, prediction run, or live-browser benchmark.
- No model recovery, held-out recovery, production readiness, public full-corpus release, private-corpus generalization, checkpoint release, or adapter release claim.

## Decisions

- Generate the extension design deterministically from committed public-safe coverage evidence.
  - Rationale: this keeps the phase reproducible and reviewable without rereading raw predictions or private corpora.
  - Alternative considered: manually draft cases in prose only. Rejected because the next materialization phase needs machine-readable candidate designs.

- Treat source families as the primary coverage unit and field labels as supporting surface evidence.
  - Rationale: the coverage assessment showed 12 source families versus 3 represented field labels; family-level breadth is the missing signal.
  - Alternative considered: only add more variants of the existing 3 fields. Rejected because it would not address the observed family coverage gap.

- Keep candidate cases design-only.
  - Rationale: materialization and public sample mutation must remain separate phases with their own validation and claim boundaries.
  - Alternative considered: generate seed/SFT rows immediately. Rejected because it would collapse design, data mutation, and later evaluation into one unreviewable step.

- Reuse the established report shape from previous form-fill evidence artifacts.
  - Rationale: existing JSON/Markdown/manifest patterns already encode public-safety, strict-metric, and no-recovery boundaries.
  - Alternative considered: a standalone markdown-only plan. Rejected because tests and downstream tooling need structured fields.

## Risks / Trade-offs

- [Risk] The extension design may be mistaken for recovery evidence. -> Mitigation: claims and artifact policy explicitly state no recovery, no prediction run, and no training.
- [Risk] Designed cases may overfit public held-out residual wording. -> Mitigation: report source-family coverage and require a later materialization/evaluation phase before any recovery claim.
- [Risk] Adding too many cases could bloat the public sample in the next phase. -> Mitigation: keep this phase design-only and recommend a bounded materialization phase separately.
- [Risk] Source-family names could expose private context. -> Mitigation: use only already committed public-safe family ids and run leak scan on outputs.
