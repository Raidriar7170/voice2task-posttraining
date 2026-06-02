## 1. A100 Smoke Configuration

- [x] 1.1 Add a dedicated public-sample A100 SFT smoke config template that keeps output under `<a100_project_root>` after private override resolution and requires explicit `--run-training` plus `allow_heavy_training: true`.
- [x] 1.2 Add a short runbook or README section for the A100 smoke workflow without hostnames, IPs, secrets, SSH details, or account-specific instructions.
- [x] 1.3 Add or update tests that prove heavy training still stays blocked unless both CLI and config opt-ins are present.

## 2. Evidence Capture

- [x] 2.1 Extend adapter/run metadata to include sanitized package versions, selected GPU identifier policy, dataset manifest ID, output paths, command summary, and `release_status: not_released`.
- [x] 2.2 Add a public-safe A100 smoke evidence manifest/report path under `reports/public-sample/` or `reports/templates/` that records SFT smoke status without copying raw remote logs or checkpoints.
- [x] 2.3 Add leak-scan coverage for the evidence pack to reject local absolute paths, secrets/tokens, private IPs, SSH details, raw private rows, and oversized generated corpora.

## 3. A100 Execution Gate

- [x] 3.1 Before any remote run, confirm A100 access, model download permission, idle GPU selection, and output placement under the approved private A100 project root.
- [x] 3.2 Run the bounded A100 public-sample SFT smoke only after confirmation, and keep raw checkpoints, adapters, logs, and caches out of git.
- [x] 3.3 Copy back only sanitized metadata, metrics, and summary evidence needed for repository validation.

Completion note: task 3.2 completed after the Hugging Face download path failed; ModelScope was used to obtain the same `Qwen/Qwen2.5-0.5B-Instruct` model ID into a private remote local snapshot and the bounded public-sample SFT smoke finished. Only sanitized metadata and summary evidence were copied back; private model cache paths, raw stderr/logs, adapters, checkpoints, and caches remain out of git.

## 4. Validation

- [x] 4.1 Run `uv run ruff check .`, `uv run mypy src`, and `uv run pytest`.
- [x] 4.2 Run the public-sample dataset build, `voice2task-data validate --public`, and `voice2task-data dpo-check` commands.
- [x] 4.3 Run `voice2task-eval metrics`, `voice2task-eval smoke`, and `voice2task-report leak-scan` against the public evidence paths.
- [x] 4.4 Run `OPENSPEC_TELEMETRY=0 openspec validate --all --strict` and `git diff --check`.
- [x] 4.5 Generate a concise Chinese Human Brief HTML summarizing the A100 smoke phase, evidence files, validation results, and claims not to overstate.
