## Context

The current committed truth surface includes additive layered evaluation under
`reports/public-sample/layered-eval/` and additive residual diagnosis under
`reports/public-sample/residual-diagnosis/`. The actual committed paths use
`dev/metrics.json`, `test/metrics.json`, `dev/residual_diagnosis.json`, and
`test/residual_diagnosis.json`; the implementation should discover these
current artifacts and may tolerate the attachment's older flat-path wording
without overwriting any historical report.

This phase is a decision artifact, not a model-quality phase. It must help pick
the next bounded OpenSpec direction by combining metric state, residual family
counts, sanitized examples, remediation strategy mapping, and at most two
ranked next targets.

## Goals / Non-Goals

**Goals:**

- Read committed layered-eval dev/test metrics and current residual-diagnosis
  dev/test artifacts.
- Aggregate dev/test residual failure-family counts, proportions, split
  distribution, affected route/task/family hints where public-safe data exists,
  and sanitized examples.
- Map high-frequency families to one of `DATA_REMEDIATION`,
  `SCHEMA_CANONICALIZATION`, `DETERMINISTIC_POSTPROCESSOR`, `SAFETY_REPAIR`, or
  `DEFER`.
- Select at most two next remediation targets using the attachment's priority
  rules, with explicit allowed operations, non-goals, expected measurable
  effects, and claim boundaries.
- Write exactly the requested report files:
  `summary.md`, `summary.json`, `top-failures.md`, and
  `recommended-next-change.md`.

**Non-Goals:**

- No training, prediction, data expansion, candidate merge, split change, DPO
  expansion, LoRA/base model change, evaluator metric change, evaluator
  relaxation, LLM judge, semantic equivalence scoring, prediction repair,
  checkpoint/adapter publication, held-out recovery claim, production-readiness
  claim, safety-readiness claim, or live-browser benchmark claim.
- No rewriting or overwriting of `reports/public-sample/layered-eval/`,
  `reports/public-sample/residual-diagnosis/`, strict evaluator artifacts, or
  historical scaled residual diagnosis/target-selection artifacts.
- No public release of local/private corpus rows or private runtime details.

## Decisions

1. **Use a small analysis module instead of extending the evaluator.**
   The new code should live beside evaluation/report utilities but only read
   existing artifacts. This keeps strict evaluator semantics intact and makes
   the phase reproducible from committed public-safe JSON.

2. **Treat residual-family names as a stable public diagnostic vocabulary.**
   The implementation should normalize current names such as `slot_value` and
   `normalized_command` into attachment-facing families such as
   `slot_value_mismatch` and `normalized_command_mismatch` while preserving the
   source family name in machine-readable output.

3. **Use deterministic strategy rules.**
   Safety-related evidence takes priority when present. Slot-key/missing/extra
   slot families map to schema/canonicalization or data remediation. Derived
   fields such as `allowed_actions` and `success_criteria` map to deterministic
   post-processing. Low-frequency non-safety families may defer.

4. **Make `recommended-next-change.md` a prompt seed, not an instruction to
   execute the next phase.**
   The current `/opsx auto` loop may continue only if a later phase is still
   bounded and allowed, but this artifact itself must not materialize data,
   change policy, train, rerun predictions, or modify evaluator semantics.

## Risks / Trade-offs

- [Risk] Attachment examples mention flat `dev.json`/`test.json` paths while
  committed artifacts use nested paths. -> Mitigation: implement explicit
  discovery with tests for the nested current layout.
- [Risk] Residual diagnosis may not include full task/route/source family
  metadata for every example. -> Mitigation: report available `field_path`,
  `row_id`, and family-derived route/task hints; use `unknown` rather than
  inventing missing metadata.
- [Risk] The top failure by count may be non-safety while a safety false
  negative exists. -> Mitigation: use the specified priority rule so safety can
  become one of the selected targets even with lower count.
- [Risk] Strategy selection could be mistaken for a permission to execute the
  next remediation. -> Mitigation: carry explicit execution scope and claim
  boundaries into JSON, Markdown, Human Brief, and OpenSpec tasks.
