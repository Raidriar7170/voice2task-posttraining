# A100 Public-Sample SFT Smoke Evidence Template

Status: `<pending_remote_run|completed|blocked>`.

This evidence pack is for a bounded public-sample SFT smoke. It is not a checkpoint release and makes no live-browser benchmark improvement claim.

## Required Sanitized Fields

- Base model
- Dataset manifest ID
- Package versions with package names and versions only
- GPU selection policy without host, private address, or GPU UUID
- Output paths under `<a100_project_root>`
- Command summary for `voice2task-train sft --run-training`
- Release status: `not_released`

## Commit Boundary

- Commit sanitized metadata, aggregate metrics, controlled smoke status, leak-scan status, and this report only.
- Do not commit raw logs, caches, checkpoints, adapters, raw private rows, host details, private addresses, tokens, or account-specific access instructions.
