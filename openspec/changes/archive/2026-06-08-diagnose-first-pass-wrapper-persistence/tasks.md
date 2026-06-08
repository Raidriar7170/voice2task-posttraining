## 1. Scope And RED Test

- [x] 1.1 Validate OpenSpec artifacts and confirm the source A100 rerun evidence exists.
- [x] 1.2 Add a focused failing test for the wrapper persistence diagnosis pack, Human Brief, public-safety boundaries, and non-claim wording.

## 2. Diagnosis Evidence

- [x] 2.1 Generate `reports/public-sample/a100-first-pass-wrapper-persistence-diagnosis/` from existing sanitized A100 rerun artifacts only.
- [x] 2.2 Record boundary visibility, Markdown wrapper counts, raw/retry parse status counts, EOS/finish-state evidence, strict schema-valid counts, and source artifact links.
- [x] 2.3 Generate `docs/human-briefs/2026-06-08-diagnose-first-pass-wrapper-persistence.html` with concise Chinese status, evidence, limitations, and recommended next step.
- [x] 2.4 Generate manifest and leak scans without private paths, host details, SSH details, private configs, raw logs, checkpoints, adapters, or private rows.

## 3. Validation, Review, Archive, Integration

- [x] 3.1 Run focused test, full `PYTHONPATH=src pytest -q`, `uv run ruff check .`, `uv run mypy src`, public data validation, DPO pair check, leak scans, `git diff --check`, and `openspec validate --all --strict`.
- [x] 3.2 Complete Reviewer pass, fix in-scope Must Fix items only, and rerun required validation.
- [x] 3.3 Archive the OpenSpec change, generate post-archive/final leak scans, rerun post-archive validation, and commit the phase under guarded auto integration.
