## 1. Diagnostic Contract

- [x] 1.1 Add focused failing tests for SFT training-vs-prediction rendering, assistant target span evidence, label-mask evidence boundaries, and adapter/base metadata comparison.
- [x] 1.2 Implement a public-safe SFT target-template alignment diagnostic that accepts public-sample rows, SFT config, prediction config, prior prediction metadata, prior objective inspection, and prior report paths.
- [x] 1.3 Add a CLI/report surface that writes JSON and Markdown evidence under `reports/public-sample/sft-target-template-alignment/`.

## 2. Evidence and Documentation

- [x] 2.1 Generate the local public-safe alignment evidence pack without running private A100 prediction or loading private adapters.
- [x] 2.2 Generate a concise Chinese Human Brief with project-stage progress, evidence links, validation results, remaining gaps, and non-overclaim boundaries.
- [x] 2.3 Run leak-scan on the alignment evidence, Human Brief, and OpenSpec change.

## 3. Validation and OpenSpec Closeout

- [x] 3.1 Run fresh validation: focused diagnostic tests, full `PYTHONPATH=src pytest -q`, `ruff check .`, `mypy src`, public dataset build/validate, DPO pair checks, schema metrics smoke, `OPENSPEC_TELEMETRY=0 openspec validate --all --strict`, and `git diff --check`.
- [x] 3.2 Run Reviewer diff review, fix in-scope Must Fix items, and rerun required validation.
- [x] 3.3 Sync accepted specs into `openspec/specs/`, archive the change, generate loop closeout HTML, and apply auto integration policy when safe.
