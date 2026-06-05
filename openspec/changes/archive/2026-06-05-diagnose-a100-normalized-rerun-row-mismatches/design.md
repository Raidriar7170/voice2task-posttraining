# Design

## Context

The previous phase archived public-safe A100 normalized-command policy rerun artifacts under `reports/public-sample/a100-normalized-command-policy-train-split-rerun/`. Those artifacts already include train gold rows, predictions, strict metrics, schema guard summaries, normalized-command diagnosis, manifest, report, and leak scans.

This phase must only explain the residual row-level mismatch shape. It must not change the prediction source, final strict metric interpretation, or row validity.

## Approach

1. Load the existing public-safe source artifacts:
   - `train_split_gold.jsonl`
   - `predictions.jsonl`
   - `metrics.json`
   - `schema_guard_summary.json`
   - `normalized_command_diagnosis.json`
   - `manifest.json`
2. Reuse field-level alignment comparison against raw prediction objects.
3. Add a narrow normalized-rerun row-mismatch classifier:
   - missing required `confirmation_required` takes precedence when schema guard records it,
   - invalid `task_type` enum takes precedence when a raw prediction has a task type outside the contract enum,
   - schema-valid rows with task/route/safety/slot differences are classified as task-route-safety-slot mismatch.
4. Write a machine-readable JSON diagnosis, Markdown report, manifest, leak-scan results, and Human Brief.
5. Validate that the source strict metrics and claim boundaries are preserved verbatim.

## Alternatives Considered

- Reuse the existing confirmation-rerun row-mismatch wrapper directly.
  - Rejected because its `diagnostic_kind` and naming bind it to the earlier confirmation-required rerun and would mislabel this normalized-command rerun.
- Add semantic equivalence for `北京 明天 天气` versus `北京明天天气`.
  - Rejected because this phase is strict evidence-only and must not alter evaluator semantics.
- Repair invalid predictions before diagnosis.
  - Rejected because invalid source predictions must remain invalid.

## Risks And Mitigations

- Risk: Readers may interpret the diagnosis as model-quality improvement evidence.
  - Mitigation: claims and Human Brief explicitly state local train-internal evidence only.
- Risk: Public artifacts leak private A100 paths.
  - Mitigation: run leak scans over evidence, Human Brief, and OpenSpec artifacts.
- Risk: The new classification hides field-level detail.
  - Mitigation: retain row-level mismatch lists and source artifact links in JSON/Markdown.
