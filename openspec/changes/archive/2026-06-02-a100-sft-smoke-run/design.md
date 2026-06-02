## Context

The archived bootstrap change established the Voice2Task post-training project, public sample data, SFT/DPO formatting, dry-run training metadata, contract metrics, controlled smoke, and public-safe reports. The real SFT path is intentionally gated behind `--run-training` and `allow_heavy_training: true`, so the repository can be validated locally without model downloads or GPU usage.

The next credibility gap is narrower than "train a model": prove that the existing TRL/PEFT SFT entrypoint can run once on the A100 development machine using only the public sample, while preserving the repository's public/private boundary. This phase should produce sanitized evidence, not a public checkpoint.

## Goals / Non-Goals

**Goals:**

- Add a bounded A100 public-sample SFT smoke workflow with explicit remote output placement under `<a100_project_root>`.
- Keep heavy training opt-in through both CLI and config gates.
- Capture sanitized run evidence: config, adapter metadata, run manifest, contract metrics, controlled smoke result, leak-scan result, and a short human-readable report.
- Verify that no public artifact contains secrets, host/IP details, raw private corpus rows, or local absolute paths.
- Document the exact manual confirmation needed before any apply phase touches the A100 environment.

**Non-Goals:**

- DPO training smoke.
- Full local/private corpus training.
- GRPO or rule-reward training.
- Publishing checkpoints, adapters, raw logs, private datasets, host details, or remote access instructions.
- Claiming live-browser benchmark improvement.

## Decisions

### Use the public sample for the first real training smoke

The smoke run will train only on the committed public sample. This keeps the evidence reproducible and reviewable while avoiding private corpus handling in the first A100 phase.

Alternatives considered:

- Use the full local/private corpus: rejected for this phase because it would mix remote execution, privacy review, and training validation.
- Use synthetic extra rows: rejected because the public sample already exercises the schema, route, safety, confirmation, slot, and DPO categories enough for a smoke run.

### Treat A100 output as private by default

All remote outputs will stay under the approved private A100 project root. The repo may only receive sanitized summaries such as metadata, metrics, and a run manifest with host/IP/secrets removed.

Alternatives considered:

- Commit the adapter or checkpoint: rejected because the project has no release-quality model evidence yet.
- Commit raw logs: rejected because logs can contain paths, hosts, environment details, or provider/cache metadata.

### Keep the existing TRL/PEFT path authoritative

The phase should use the existing `voice2task-train sft --run-training` entrypoint instead of introducing ms-swift as the primary path. ms-swift remains a later engineering route after the transparent stack is proven.

Alternatives considered:

- Add ms-swift now: rejected because it expands dependencies and obscures whether the primary public implementation works.
- Rewrite training around a custom loop: rejected because the bootstrap already scoped Transformers + PEFT + TRL as the transparent first implementation.

### Validate evidence locally after remote execution

The apply phase should copy back only sanitized evidence, then run local tests, OpenSpec validation, leak scan, and diff checks. Remote success alone is not sufficient.

Alternatives considered:

- Trust the remote training exit code: rejected because public claims depend on repo-local artifacts and validation.

## Risks / Trade-offs

- A100 access or model download may be unavailable -> stop before apply if access, credentials, or network/model terms are not available.
- Real TRL/PEFT versions may differ from local dev assumptions -> pin the observed package versions in sanitized metadata and avoid broad dependency rewrites unless required.
- Public sample is tiny -> report this as an execution smoke only, not model quality evidence.
- Raw remote logs may contain sensitive paths or host details -> keep them out of git and generate a sanitized summary instead.
- The smoke may fail due to memory, tokenizer, or trainer API drift -> capture the failure in a private remote log and update tasks/specs before expanding scope.

## Migration Plan

This change adds a new opt-in evidence workflow and does not alter existing dry-run defaults. Rollback is removing the new config/runbook/evidence files and leaving the archived bootstrap specs intact.

## Apply Confirmation Gate

- Use `Qwen/Qwen2.5-0.5B-Instruct` for the smoke. If that checkpoint is unavailable or too slow on the selected GPU, stop and confirm a replacement before changing scope.
- Commit only sanitized adapter metadata, run manifest, aggregate metrics, controlled smoke result, leak-scan result, and a human-readable report. Do not add a new prediction sample unless it is derived only from the already committed public sample and passes leak scan.
