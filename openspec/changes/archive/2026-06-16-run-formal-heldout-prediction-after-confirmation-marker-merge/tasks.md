## 1. Readiness

- [x] 1.1 Verify repo status, active OpenSpec status, current manifest id/counts, formal-heldout config templates, existing held-out evidence, and post-merge output directory plan.
- [x] 1.2 Run an Explorer pass or local pattern review for the current prediction export, evaluation, report, leak-scan, and A100 evidence import patterns.
- [x] 1.3 Attempt A100 GPU/process occupancy and private adapter availability inspection under the approved private project root without writing public artifacts or exposing private paths. Outcome: blocked by SSH timeout before GPU/process/adapter details were available.

## 2. Prediction-Only Execution

- [x] 2.1 Prepare private, repo-external A100 dev/test prediction configs or overrides resolving placeholders to approved private paths and the selected adapter. Outcome: public templates now point at the distinct post-merge evidence directory; private overrides were not written because remote access was unavailable.
- [x] 2.2 Run dev/test prediction-only exports with explicit `CUDA_VISIBLE_DEVICES`, no training flags, and sidecars needed for public-safe evidence. Outcome: not launched because the fail-closed blocked branch in 2.3 was triggered before GPU selection.
- [x] 2.3 If prediction cannot safely run, write blocked-status evidence instead of predictions or model-quality metrics.

## 3. Public Evidence

- [x] 3.1 Import or generate sanitized dev/test predictions, prediction metadata, prompt/decoded sidecars where available, metrics, failure slices, manifest, and Markdown report under a distinct post-confirmation-marker-merge evidence directory. Outcome: generated fail-closed blocked evidence under the distinct directory, with no predictions, model-quality metrics, or failure slices.
- [x] 3.2 Ensure reports record manifest id `public-sample-20260616T074315Z`, dev/test split row counts, 98/252/850 source counts, strict metric authority, and boundary-changed comparison semantics.
- [x] 3.3 Generate `docs/human-briefs/2026-06-16-run-formal-heldout-prediction-after-confirmation-marker-merge.html`.

## 4. Validation And Review

- [x] 4.1 Run focused tests or report-generation checks for the new evidence, plus public dataset validation, DPO check, leak scan, `ruff check .`, `PYTHONPATH=src python3 -m pytest -q`, `OPENSPEC_TELEMETRY=0 openspec validate --all --strict`, and `git diff --check`.
- [x] 4.2 Run a Reviewer pass and fix in-scope Must Fix items.
- [x] 4.3 Archive the OpenSpec change after tasks complete and validation passes.
