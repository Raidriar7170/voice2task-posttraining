## Context

The existing SFT entrypoint has three fail-open boundaries: output paths are checked before canonicalization and may be unrooted, blocked CLI results can exit successfully, and a real run can bypass a separately performed readiness check. This change is an infrastructure-only prerequisite for one private, explicitly selected A100, one or two formal-public train rows, and exactly one optimizer step. It does not change the clean-evaluation truth surface or authorize broader model work.

## Goals / Non-Goals

**Goals:**

- Make output placement fail closed against missing roots, relative paths, traversal, symlinks, non-empty destinations, tracked repository paths, and preflight-to-load drift.
- Expose one shared, machine-readable, public-safe SFT preflight used by both the CLI and the real training path before model-weight loading.
- Wire a local-only Qwen2.5-7B-Instruct BF16 LoRA smoke configuration through model loading, training arguments, metadata, and postconditions.
- Return one JSON document and an exit status that accurately distinguishes success from blocked, skipped, unavailable, or failed execution.

**Non-Goals:**

- Full or 282-row SFT, DPO, GRPO, prediction, evaluation, lockbox access, public adapter release, deployment, or any model-improvement/readiness claim.
- Relaxing or rewriting any clean-evaluation blocker.
- Discovering private model or output paths outside the explicitly supplied ignored config.

## Decisions

### 1. One structured preflight report is the execution gate

`_run_sft_preflight_core` is the exception-safe shared gate and returns two products from one execution: a schema-versioned public JSON-compatible report and, only when ready, a frozen private execution context. The context binds canonical config, manifest, SFT, selected rows, the exact model facts returned by the validated probe, and output facts by hashes and immutable JSON snapshots. The public `run_sft_preflight` wrapper discards the private context. Real `run_sft(..., run_training=True)` calls this shared gate before any legacy config, metadata, or dataset read; blocked execution returns a minimal no-write result, while ready metadata is constructed only from the bound report and context. The real runner rehashes config, manifest, the complete SFT file, and model inventory immediately before model/tokenizer loading. Dataset selection and model-inventory binding do not run on second, weaker paths around preflight.

Alternative considered: keep a lightweight CLI preflight and separate runtime guards. Rejected because the paths can drift and the real run could become less strict than the audit command.

### 2. Output authorization is based on canonical filesystem identity

The output root and candidate parent must already exist, be absolute directories, and not be symlinks. Preflight binds both objects' `st_dev`, `st_ino`, `st_uid`, `st_gid`, and `st_mode` in the private execution context. The runner opens root-to-parent components descriptor-relatively with directory/no-follow flags and creates only the final leaf with `os.mkdir(..., mode=0o700, dir_fd=parent_fd)`. It compares `fstat` identity before and after claim and never performs pathname cleanup once identity becomes uncertain. DPO uses the same claim primitive defensively without authorizing execution.

Threat-model clarification authorized by the user: these checks defend every drift, symlink, inode-exchange, and concurrent-leaf condition observable at a checkpoint. They do not claim that userspace identity comparison and the following `mkdirat` syscall are one kernel-atomic operation. Production use therefore requires the output root and parent namespace not be maliciously renamed by another same-UID process during that final boundary.

Alternative considered: lexical `Path.relative_to`. Rejected because it does not defend against `..`, symlink redirection, or later path substitution.

### 3. Public results are strict allowlists; blockers are stable codes

Exceptions and machine-specific values are converted to enumerated blocker codes. CLI training output is rebuilt from an exact top-level allowlist and a separately allowlisted adapter-file inventory; it never recursively sanitizes or copies the private metadata object. Public JSON may include only approved schema/status, blockers, preflight, budget/metrics, adapter filename-size-hash evidence, and the unchanged clean-evaluation facts. Private execution metadata remains only in the ignored output directory.

Alternative considered: surface exception strings for convenience. Rejected because they are unstable and can leak private runtime details.

### 4. Dataset and objective validation precede model weights

The canonical formal manifest and complete SFT JSONL are hashed. After binding the current manifest ID and exact SFT entry, parsing reads from the beginning, requires `split=train` for every selected record, stops immediately after the configured one or two rows, rejects duplicates/empty selections and `train_source_ids`, and hashes the ordered selected IDs. Smoke budget scalars use exact JSON integer semantics: `max_train_rows` is a non-boolean integer in `{1, 2}`; `max_steps`, `per_device_train_batch_size`, and `gradient_accumulation_steps` are non-boolean integer `1`; `max_seq_length` is a non-boolean integer from 1 through 4096; `seed` is a non-boolean integer; and `logging_steps` is a positive non-boolean integer. Those exact serialized rows are carried in the private context. A local tokenizer constructs the same assistant-only records used by training and verifies mask, target, length, and tensor-shape invariants before the 7B model is loaded.

### 5. The trainer owns one explicitly visible idle GPU

The caller must set `CUDA_VISIBLE_DEVICES`, exactly one device must be visible, the name must identify an A100, BF16 and compute capability must pass, total and current free memory must each be at least 35 GiB, and a sanitized compute-process probe must count zero processes. The same probe runs again immediately before weights load. Public facts expose only aggregate count and readiness, never process identity.

### 6. Smoke completion is a narrow postcondition

`SMOKE_COMPLETED` additionally requires a positive trainable-parameter count, positive adapter-tensor count, stable before/after adapter-state digests, at least one changed adapter tensor, and finite values for every adapter tensor. Adapter files carry filename, size, and SHA-256. A step count and files alone never prove an update.

## Risks / Trade-offs

- [Filesystem state changes after preflight] -> Bind root/parent identities and use descriptor-relative no-follow traversal plus leaf-only mkdir; fail closed without pathname cleanup on uncertainty.
- [Same-UID rename at the final syscall boundary] -> This narrow interval is an explicit deployment precondition, not a claimed atomic defense; prevent malicious same-UID namespace renames during claim.
- [Tokenizer loading itself can be expensive] -> Keep it local-only and load it before model weights because objective validity depends on the real tokenizer.
- [Git status includes generated private ignored config] -> Inspect tracked changes only and record commit SHA; ignored files never make readiness dirty.
- [Package/GPU APIs vary between versions] -> Keep dependency and GPU probes injectable for unit tests and convert failures to stable blockers.
- [A smoke can be mistaken for evaluation] -> Preserve all seven clean-evaluation blockers and use only `SMOKE_COMPLETED`.

## Migration Plan

1. Add failing unit/CLI tests for the new contracts.
2. Add the shared preflight and output policy, then wire the CLI and runtime path.
3. Add bounded Qwen2.5-7B runtime options and the disabled public example.
4. Run focused and repository-wide static/test/OpenSpec/truth checks.
5. Run a private preflight only if an explicitly supplied ignored config exists; run the single authorized smoke only if it returns `ready=true` on an idle explicitly selected A100.

Rollback is a code revert. Private outputs and configs remain ignored and are never migration inputs.

## Open Questions

None. The requested budget, model identity, data split, blocker vocabulary, and prohibited actions are explicit.
