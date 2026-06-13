## 1. Proposal And Local Preparation

- [x] 1.1 Create OpenSpec proposal, design, specs, and tasks for public held-out prediction-only evaluation.
- [x] 1.2 Add public-safe `dev` and `test` A100 prediction config templates for the existing canonical wording adapter.
- [x] 1.3 Add focused tests that the templates are 7B, prediction-only, split-specific, public-safe, and do not claim private/general production readiness.

## 2. A100 Prediction Execution

- [x] 2.1 Inspect A100 GPU occupancy and verify the previous private canonical wording adapter exists under the approved private project root.
- [x] 2.2 Sync only required public-safe files to the approved A100 project root.
- [x] 2.3 Run prediction-only exports for public `dev` and `test`, setting `CUDA_VISIBLE_DEVICES` explicitly.
- [x] 2.4 Copy back only sanitized predictions and sidecars.

## 3. Evidence And Reporting

- [x] 3.1 Generate split-specific gold JSONL, strict metrics, schema diagnostics, alignment diagnostics, and constrained decoding diagnostics.
- [x] 3.2 Generate a combined held-out diagnosis, manifest, report, leak scans, and concise Chinese Human Brief.
- [x] 3.3 Run focused and full local validation: `PYTHONPATH=src pytest -q`, `uv run ruff check .`, `uv run mypy src`, public data validate, OpenSpec strict, public leak scan, and `git diff --check`.

## 4. Review And Archive

- [x] 4.1 Perform a read-only diff/evidence review for Must Fix issues and rerun affected validation.
- [x] 4.2 Archive the OpenSpec change after successful validation and rerun post-archive validation.
