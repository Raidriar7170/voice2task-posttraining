## 1. Label Provenance Contract

- [x] 1.1 Add focused failing tests for inspectable collator labels, unavailable tokenizer/collator states, fixture-label source boundaries, and CLI output shape.
- [x] 1.2 Extend SFT objective inspection to report tokenizer/template status, collator status, label source, label tensor availability, prompt mask status, assistant-target loss status, and bounded loss interpretation without raw rendered text.
- [x] 1.3 Preserve backward-compatible objective-inspection fields consumed by existing diagnostics.

## 2. Evidence and Documentation

- [x] 2.1 Generate a public-safe label provenance evidence pack under `reports/public-sample/sft-label-provenance/` with JSON and Markdown summaries.
- [x] 2.2 Link prior train-split and target-template diagnostics without modifying their artifacts.
- [x] 2.3 Generate a concise Chinese Human Brief with project-stage progress, evidence links, validation results, remaining gaps, and non-overclaim boundaries.

## 3. Validation and OpenSpec Closeout

- [x] 3.1 Run fresh validation: focused tests, full `PYTHONPATH=src pytest -q`, `ruff check .`, `mypy src`, public dataset validate, DPO pair checks, schema metrics smoke, `OPENSPEC_TELEMETRY=0 openspec validate --all --strict`, leak-scan, and `git diff --check`.
- [x] 3.2 Run Reviewer diff review, fix in-scope Must Fix items, and rerun required validation.
- [x] 3.3 Sync accepted specs into `openspec/specs/`, archive the change, generate loop closeout HTML, and apply auto integration policy when safe.
