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

The output root must already exist, be absolute, and not itself be a symlink. The absolute candidate is rejected if it equals the root, if any existing component is a symlink, if its resolved location is not a strict descendant of the resolved root, if it already exists (including an empty directory), or if it falls within the repository. Writability and free space are checked on the nearest existing parent. The real runner claims the final directory with exclusive creation, then accepts only the expected existing-empty result from the same policy and the bound path hash. DPO real mode derives its repository root from the supplied manifest checkout with a cwd-independent fail-closed helper, passes that root explicitly to its runner, uses the same generic gate before metadata/dependency work, and repeats it in the runner. This is defensive hardening, not authorization to execute DPO.

Alternative considered: lexical `Path.relative_to`. Rejected because it does not defend against `..`, symlink redirection, or later path substitution.

### 3. Blockers are stable codes; diagnostics are sanitized sections

Exceptions and machine-specific values are converted to enumerated blocker codes. The shared top-level gate catches unexpected internal exceptions and returns the complete blocked schema with only `PREFLIGHT_INTERNAL_ERROR`; it never serializes the exception. Public config facts are an explicit whitelist of approved constants, booleans, bounded numbers, and hashes. Public JSON includes hashes, booleans, counts, versions, GPU model/capability/memory, and file-name/size inventories, but not private paths, hostname, IP, GPU UUID, secrets, environment values, arbitrary config strings, or raw exception text.

Alternative considered: surface exception strings for convenience. Rejected because they are unstable and can leak private runtime details.

### 4. Dataset and objective validation precede model weights

The canonical formal manifest and complete SFT JSONL are hashed. After binding the current manifest ID and exact SFT entry, parsing reads from the beginning, requires `split=train` for every selected record, stops immediately after the configured one or two rows, rejects duplicates/empty selections and `train_source_ids`, and hashes the ordered selected IDs. Smoke budget scalars use exact JSON integer semantics: `max_train_rows` is a non-boolean integer in `{1, 2}`; `max_steps`, `per_device_train_batch_size`, and `gradient_accumulation_steps` are non-boolean integer `1`; `max_seq_length` is a non-boolean integer from 1 through 4096; `seed` is a non-boolean integer; and `logging_steps` is a positive non-boolean integer. Those exact serialized rows are carried in the private context. A local tokenizer constructs the same assistant-only records used by training and verifies mask, target, length, and tensor-shape invariants before the 7B model is loaded.

### 5. The trainer owns one explicitly visible GPU

The caller must set `CUDA_VISIBLE_DEVICES`, exactly one CUDA device must be visible, the device name must identify an A100, BF16 must be supported, compute capability must meet the BF16 threshold, and memory must be at least 35 GiB. The private model must match Qwen2.5-7B-Instruct geometry and architecture, expose at least 12 GiB of weight inventory, use `dtype=torch_dtype=bfloat16`, `trust_remote_code=false`, local-only loading, and a bounded q/k/v/o LoRA target set. Model loading does not use `device_map="auto"`; Trainer/Accelerate performs placement. Gradient checkpointing forces `use_cache=false`. A missing pad token uses only the tokenizer EOS token after validation.

### 6. Smoke completion is a narrow postcondition

`SMOKE_COMPLETED` requires exit success, `training_completed`, one true integer optimizer step, an observed row count exactly equal to configured `max_train_rows`, a finite non-boolean numeric loss, and both non-empty `adapter_config.json` and adapter weights. The entire run tree is scanned for full base-model files, indexes, or shards rather than checking only the adapter directory. Metadata records the bounded budget and public-safe provenance. Any mismatch is a failed run, not a partial success.

## Risks / Trade-offs

- [Filesystem state changes after preflight] -> Rehash bound inputs, repeat policy, claim the final output directory exclusively, and post-claim revalidate before local tokenizer/model loading. Parent-component mutation after the final check would require a directory-fd based redesign to eliminate completely.
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
