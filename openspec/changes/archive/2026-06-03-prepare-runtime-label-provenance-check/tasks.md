## 1. Runtime Preparation Contract

- [x] 1.1 Add focused failing tests for runtime label provenance config template validation, unresolved private override blocking, non-heavy default behavior, and readiness metadata shape.
- [x] 1.2 Implement runtime label provenance preparation metadata without downloading models, loading private adapters, connecting to A100, or inspecting private labels.
- [x] 1.3 Add a committed public-safe runtime config template with unresolved private placeholders and explicit private override requirements.

## 2. Evidence and Documentation

- [x] 2.1 Generate a public-safe runtime label provenance preparation evidence pack under `reports/public-sample/runtime-label-provenance-prep/`.
- [x] 2.2 Link prior label provenance, target-template, and train-split diagnostic artifacts without modifying them.
- [x] 2.3 Generate a concise Chinese Human Brief with project-stage progress, validation results, remaining gaps, and non-overclaim boundaries.

## 3. Validation and OpenSpec Closeout

- [x] 3.1 Run fresh validation: focused tests, full `PYTHONPATH=src pytest -q`, `ruff check .`, `mypy src`, public dataset validate, DPO pair checks, schema metrics smoke, `OPENSPEC_TELEMETRY=0 openspec validate --all --strict`, leak-scan, and `git diff --check`.
- [x] 3.2 Run Reviewer diff review, fix in-scope Must Fix items, and rerun required validation.
- [x] 3.3 Sync accepted specs into `openspec/specs/`, archive the change, generate loop closeout HTML, and apply auto integration policy when safe.
