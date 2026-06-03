## Context

The repository now has a public-safe local SFT label provenance evidence pack, but the evidence correctly remains `true_label_mask_status=unavailable` because no real tokenizer/collator runtime labels were inspected. The next useful step is to prepare a gated runtime-check path that can be run later in an authorized private/A100 environment while keeping the public repo free of private paths, raw logs, checkpoints, adapters, and overclaims.

This phase is preparation only. It should make runtime readiness auditable from the public repo, fail closed when a private override is missing or unresolved, and define the evidence format expected from a later real runtime check.

## Goals / Non-Goals

**Goals:**

- Add a public-safe config template for runtime label provenance checks with unresolved private placeholders and explicit private override requirements.
- Add CLI/report behavior that records readiness, blocked/skipped states, output-root policy, runtime dependency policy, label provenance intent, and prior evidence links.
- Validate that default local runs do not download models, load private adapters, connect to A100 infrastructure, or claim true label evidence.
- Generate a Human Brief and evidence pack showing that this phase prepared the runtime check path but did not execute it.

**Non-Goals:**

- No actual A100 connection, remote SSH use, private adapter load, model download, heavy training, private corpus processing, checkpoint/adaptor release, public full-corpus release, live-browser benchmark claim, generic chat fine-tuning, skill routing, GUI action-policy learning, or first-phase GRPO.

## Decisions

1. Add preparation metadata to the existing objective-inspection/report path rather than running private infrastructure.
   - Rationale: The prior evidence pack already anchors label provenance interpretation; a preparation layer can reuse that contract and stay public-safe.
   - Alternative considered: immediately run the A100/runtime check. Rejected because it requires private infrastructure and explicit runtime details outside this phase.

2. Require private override validation before runtime execution.
   - Rationale: Committed config templates must never contain private paths or host details. The template should remain unresolved and explicitly blocked locally.
   - Alternative considered: commit a resolved local path for convenience. Rejected because it would leak machine-specific details and weaken the A100 root boundary.

3. Separate `runtime_check_status` from `true_label_mask_status`.
   - Rationale: Readiness to run is not proof that labels were inspected. Reports must make that distinction obvious.
   - Alternative considered: reuse only `inspection_status`. Rejected because `inspection_status` describes evidence availability, not run authorization or private override readiness.

4. Keep evidence generation deterministic and small.
   - Rationale: Public artifacts should be reviewable and leak-scannable, with links to prior evidence rather than raw runtime dumps.
   - Alternative considered: reserve evidence generation until after real runtime execution. Rejected because reviewers need to see the contract before private execution.

## Risks / Trade-offs

- [Risk] Preparation artifacts may be mistaken for runtime proof -> Mitigation: include `runtime_check_status`, `true_label_mask_status`, and explicit non-claim fields in JSON, Markdown, and Human Briefs.
- [Risk] Private override requirements may drift from actual A100 setup -> Mitigation: keep requirements structural and public-safe, and require the later runtime phase to record resolved evidence privately before committing sanitized summaries.
- [Risk] Additional CLI surface adds maintenance cost -> Mitigation: keep it a small extension of existing `voice2task-report` and objective-inspection metadata patterns.
- [Risk] Users may expect this phase to run the real check -> Mitigation: name the change `prepare-*` and make non-execution explicit in OpenSpec artifacts and reports.
