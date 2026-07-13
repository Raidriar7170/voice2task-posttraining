## Why

The current SFT entrypoint can accept an unconfigured or path-escaping output directory, can return exit code 0 for blocked work, and has no single auditable preflight that proves a real private Qwen2.5-7B one-step run is bounded before model weights are loaded. This change closes those fail-open boundaries while preserving every existing clean-evaluation blocker and claim limitation.

## What Changes

- **BREAKING**: Require every `sft --run-training` invocation to use an existing absolute non-symlink `output_root` and an absolute child `output_dir` that does not already exist, remains under the resolved root, and stays outside repository paths.
- Add stable, sanitized output-policy blocker codes, check the nearest existing parent, claim the final directory exclusively, and repeat the same policy immediately before model loading so preflight-to-run path drift fails closed. Apply the same generic real-training output gate to DPO without authorizing DPO execution.
- Add `voice2task-train sft-preflight` with one shared internal core that returns a public report plus a private immutable execution context covering Git state, bounded config, dependencies, explicit one-GPU BF16 runtime, formal public train-row selection, assistant-only objective construction, local-only model identity/fingerprints, and output capacity. Real SFT consumes only the bound context and rehashes mutable inputs before model loading.
- Make blocked, skipped, unavailable, and runtime-failed CLI results non-zero while preserving one JSON document on stdout and no competing result JSON on stderr.
- Wire private Qwen2.5-7B-Instruct BF16/local-only LoRA SFT options through tokenizer, model loading, `TrainingArguments`, gradient checkpointing, adapter writing, and metadata, with exact Qwen2.5-7B geometry, A100, minimum weight-inventory size, `trust_remote_code=false`, and bounded LoRA checks.
- Add a public-safe disabled-by-default example config; only an ignored private config may contain real model/output paths and enable heavy training.
- Permit at most one explicitly selected A100, one or two formal-public train rows, and exactly one optimizer step for `SMOKE_COMPLETED`; do not authorize broader execution.
- Preserve the clean-evaluation truth surface exactly: `acquisition_source_status=UNAVAILABLE`, `authoritatively_bound_binding_count=0`, `human_acceptance_status=NOT_RECORDED`, `protocol_freeze_status=NOT_FROZEN`, `clean_population_status=NOT_MATERIALIZED`, `freeze_authorized=false`, and `execution_readiness=false`.
- Add no-network/no-GPU unit tests for output traversal/symlinks/TOCTOU, direct-runner/DPO bypasses, CLI exit semantics, dependency/GPU/model/data/objective/output preflight blockers, immutable context drift, strict smoke postconditions, and model/training option propagation.

Non-goals are full or 282-row SFT, DPO, first-phase GRPO, prediction, evaluation, lockbox or clean-population access, generic chat fine-tuning, skill routing, GUI action-policy learning, public full-corpus release, checkpoint or adapter release, model-improvement claims, clean-evaluation readiness, production readiness, merge, deploy, or release.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `supervised-contract-tuning`: Strengthen the real SFT execution contract with a shared fail-closed private A100 smoke preflight, safe output policy, bounded Qwen2.5-7B runtime options, stable CLI outcomes, and truthful smoke metadata.

## Impact

- Code: `src/voice2task/training.py`, `src/voice2task/cli/train.py`.
- Configuration: new public-safe `configs/sft-a100-smoke.example.json`; an optional ignored private override remains outside Git.
- Tests: focused training/preflight/CLI tests that never require CUDA, load real model weights, or access the network.
- Runtime dependencies: checks now include Python, `torch`, `accelerate`, `datasets`, `peft`, `transformers`, `trl`, and `pip check`; no dependency is added to the project core install.
- Evidence boundary: infrastructure smoke success proves only a real gradient update, one optimizer step, adapter write, and training-path viability. It does not change clean-evaluation readiness or any model-quality claim.
