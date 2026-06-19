## 1. Test-First Coverage

- [x] 1.1 Add focused tests for current-boundary prediction config templates
  that bind dev/test to `public-sample-20260619T090925Z`, preserve private
  override placeholders, and keep source adapter lineage explicit.
- [x] 1.2 Add focused tests for observed-or-blocked current-boundary evidence,
  strict metric authority, comparison-boundary warnings, and fail-closed claim
  boundaries.
- [x] 1.3 Add focused tests that committed evidence, status docs, OpenSpec
  artifacts, and Human Brief output remain public leak-scan clean.

## 2. Local Preparation

- [x] 2.1 Add or update prediction config templates for the current canonical
  formal public sample dev/test baseline.
- [x] 2.2 Add any small report/manifest helper needed to distinguish target
  manifest id from source adapter training manifest id.
- [x] 2.3 Prepare local evidence directory structure under
  `reports/public-sample/a100-current-canonical-boundary-prediction-baseline/`.

## 3. Observed-Or-Blocked Runtime Evidence

- [x] 3.1 Run A100 preflight without exposing host, SSH, private path, or raw log
  details in committed artifacts.
- [x] 3.2 If safe, run dev/test prediction-only exports for
  `public-sample-20260619T090925Z` with the existing private
  `a100-current-train-split-sft-retry` adapter and collect sanitized
  predictions, metrics, metadata, prompt snapshots, raw decoded summaries, and
  generation traces.
  - Preflight result: not safe to continue because sanitized read-only A100 SSH
    preflight timed out; no private prediction was launched.
- [x] 3.3 If unsafe or unavailable, write blocked evidence with blocked reason
  and no fabricated predictions or metrics.

## 4. Documentation and Human Brief

- [x] 4.1 Update `CONTEXT.md` and `reports/final_status.md` with the new
  current-boundary prediction-only evidence or blocked evidence.
- [x] 4.2 Generate
  `docs/human-briefs/2026-06-19-run-current-canonical-boundary-prediction-baseline.html`.
- [x] 4.3 Keep prior `public-sample-20260617T152259Z` model evidence explicitly
  labeled historical and not directly comparable.

## 5. Review, Validation, and Archive

- [x] 5.1 Run Worker implementation in the approved current workspace with
  minimal task-related changes.
- [x] 5.2 Run Reviewer diff review and address in-scope Must Fix items.
- [x] 5.3 Run focused tests, full `python -m pytest -q`, `uv run ruff check .`,
  public dataset validation, DPO check, `openspec validate --all --strict`,
  public leak-scan, and `git diff --check`.
  - Worker note: focused pytest, full pytest, ruff, read-only public dataset
    validation, DPO check, OpenSpec `--all --strict`, current artifact/docs
    leak scan, and `git diff --check` were run.
- [x] 5.4 Archive the completed OpenSpec change only after validation and
  review pass.
