## MODIFIED Requirements

### Requirement: Run A100 public-sample SFT smoke
The system SHALL provide a bounded, opt-in, local-only Qwen2.5-7B-Instruct LoRA SFT smoke workflow that uses an explicitly selected single GPU, trains one or two rows from the current formal public sample `train` split for exactly one optimizer step, and writes private outputs only beneath an approved output root.

#### Scenario: Launch smoke with explicit opt-in
- **WHEN** a developer launches SFT with `--run-training`, a private ignored config whose `allow_heavy_training` is `true`, and a shared preflight result whose `ready` is `true`
- **THEN** the system repeats the shared preflight before model weights load, uses only the configured local Qwen2.5-7B-Instruct runtime, and records public-safe Git, config, dataset, model, dependency, GPU, output, objective, and actual-budget metadata

#### Scenario: Bound successful execution
- **WHEN** the authorized smoke completes
- **THEN** it reports `SMOKE_COMPLETED`, exactly one observed optimizer step, one or two training rows, finite loss, and non-empty adapter files without saving or copying full base-model weights

#### Scenario: Reject accidental heavy training
- **WHEN** a developer launches the training path without `--run-training`, with `allow_heavy_training` false, or with any budget outside the approved smoke bounds
- **THEN** the system does not load model weights or start training and returns a non-success training status with a stable blocker where applicable

#### Scenario: Keep remote evidence private by default
- **WHEN** a preflight or smoke produces private paths, configs, adapters, caches, or raw logs
- **THEN** those values and artifacts remain out of Git and CLI JSON is rebuilt from the exact approved result-field allowlist, with adapter evidence limited to filename, size, and SHA-256

#### Scenario: Preserve clean-evaluation blockers
- **WHEN** infrastructure preflight or the authorized smoke succeeds
- **THEN** the system leaves `acquisition_source_status=UNAVAILABLE`, `authoritatively_bound_binding_count=0`, `human_acceptance_status=NOT_RECORDED`, `protocol_freeze_status=NOT_FROZEN`, `clean_population_status=NOT_MATERIALIZED`, `freeze_authorized=false`, and `execution_readiness=false`

## ADDED Requirements

### Requirement: Enforce canonical SFT output boundaries
Every real SFT run MUST require an existing absolute non-symlink output root and an absolute, not-yet-existing, strict descendant output directory after canonical resolution. The system MUST reject traversal, any existing symlink component, final-directory symlinks, root-external destinations, every existing candidate including an empty directory, and repository locations with stable blocker codes. The exact candidate parent MUST already exist and pass the output checks before the system claims the final directory exclusively and revalidates the bound path before model and tokenizer loading.

This contract defends output drift, symlink substitution, inode exchange, and concurrent final-leaf creation that is observable at its identity checkpoints. Its deployment precondition is that no malicious same-UID process renames the output-root or candidate-parent namespace during the final identity-checkpoint-to-`mkdirat` syscall window. The contract does not claim kernel-atomic protection against such a same-UID rename inside that narrow window.

#### Scenario: Reject an unsafe output path
- **WHEN** the root is missing, relative, symlinked, or the candidate is relative, equal to the root, escaping, symlinked, already exists, or is inside the repository
- **THEN** the system returns an output-policy blocker without creating or writing metadata into the unsafe candidate

#### Scenario: Accept a new canonical child
- **WHEN** the existing absolute root is not a symlink and the absolute candidate is a new writable strict descendant with no symlink components and sufficient free space
- **THEN** output policy reports the canonical path hash as ready without exposing the path

#### Scenario: Detect preflight-to-load drift
- **WHEN** filesystem state makes a previously accepted output path unsafe before tokenizer or model loading
- **THEN** the repeated shared policy blocks execution before model weights load

#### Scenario: Claim the leaf without following exchanged paths
- **WHEN** preflight accepts an existing root and parent
- **THEN** the private context binds their filesystem identities and the runner traverses directory descriptors without following symlinks, creates only the final leaf with mode `0700`, and fails closed on any root/parent identity change or concurrent leaf creation without pathname cleanup

#### Scenario: Enforce the deployment namespace precondition
- **WHEN** a deployment permits another same-UID process to rename the accepted output root or parent during the final identity-checkpoint-to-`mkdirat` boundary
- **THEN** that deployment is outside this claim contract and MUST prevent that adversarial namespace mutation before authorizing a real smoke

### Requirement: Provide one shared SFT preflight
The system MUST expose `sft-preflight` and MUST use the same internal preflight core from real SFT execution before loading model weights. That core MUST produce the public report plus an immutable private execution context binding canonical inputs, selected rows, model inventory, and output facts. Real training MUST consume the bound context rather than reselecting data from caller arguments and MUST rehash mutable inputs before model loading. The single public JSON result MUST use schema `voice2task-sft-preflight-v1`, report `ready`, `status`, `blockers`, and the `git`, `config`, `dataset`, `model`, `runtime`, `gpu`, `output`, and `objective` sections, and MUST not access the network.

#### Scenario: Report a ready bounded smoke
- **WHEN** Git tracked state is clean and includes the change, the ignored non-symlink private config is exactly smoke-bounded, dependencies and `pip check` pass, one explicit idle BF16-capable A100 has at least 35 GiB total and free memory and zero compute processes, exact local Qwen2.5-7B model/tokenizer identity and >=12 GiB weight inventory pass, selected formal train rows and assistant-only labels pass, and output policy passes
- **THEN** preflight returns exit code 0 with `ready=true`, an empty blocker list, stable fingerprints, hashes, versions, counts, and public-safe facts

#### Scenario: Report blocked readiness safely
- **WHEN** any required Git, config, dependency, GPU, model, dataset, objective, or output condition fails
- **THEN** preflight returns non-zero with `ready=false` and only stable enumerated blocker codes, including `GPU_FREE_MEMORY_INSUFFICIENT`, `GPU_BUSY`, or `GPU_OCCUPANCY_PROBE_FAILED` for the corresponding GPU state, without raw exceptions or private runtime values

#### Scenario: Fail closed on an unexpected preflight exception
- **WHEN** any internal shared-preflight operation raises an unexpected exception
- **THEN** both `sft-preflight` and real SFT return the complete blocked preflight schema with only `PREFLIGHT_INTERNAL_ERROR`, do not serialize exception text or private values, and do not write the candidate output

#### Scenario: Consume only the bound ready context
- **WHEN** real SFT reaches a ready shared preflight result
- **THEN** it builds execution metadata only from the bound report and immutable context, without rereading legacy config, manifest, or dataset inputs around the gate, and binds the exact model facts produced by the validated model probe

### Requirement: Keep smoke row selection and objective exact
The shared preflight MUST require the canonical current formal manifest and exact SFT entry, hash both complete files, then parse only the first exactly `max_train_rows` ordered `split=train` records where that value is a non-boolean integer in `{1, 2}` and stop. It MUST reject JSON booleans and floats for `max_train_rows`, `max_steps`, `per_device_train_batch_size`, and `gradient_accumulation_steps`; the latter three MUST be the non-boolean integer `1`. It MUST also require `seed` to be a non-boolean integer and `logging_steps` to be a positive non-boolean integer before those values reach real `TrainingArguments`. It MUST reject empty or duplicate row IDs and every implicit selector such as `train_source_ids`, bind those exact rows into the private execution context, and validate every selected row with the same real-tokenizer assistant-only record builder used for training.

#### Scenario: Validate assistant-only records
- **WHEN** a selected row is encoded with tokenizer offsets
- **THEN** every token outside the contiguous assistant target region has label `-100`, every assistant label matches its input token, at least one assistant token carries loss, all tensor lengths match, and length does not exceed the validated `max_seq_length`

#### Scenario: Prove a real adapter update
- **WHEN** one-step training returns
- **THEN** smoke completion additionally requires positive trainable/adapter tensor counts, different stable before/after adapter-state digests, at least one changed adapter tensor, finite adapter values, and hashed non-empty adapter files

#### Scenario: Reject data or selection drift
- **WHEN** the manifest/SFT hash or manifest ID does not match its declared value, train selection changes, rows are empty or duplicated, labels are invalid, or sequence length is exceeded
- **THEN** preflight fails with a stable dataset or objective blocker before model weights load

#### Scenario: Reject numeric type coercion
- **WHEN** a smoke budget, seed, or logging field uses a JSON boolean or float where an integer is required, or `logging_steps` is not positive
- **THEN** preflight returns `CONFIG_NOT_SMOKE_BOUNDED`; a malformed `max_train_rows` additionally returns `TRAIN_ROW_SELECTION_INVALID` and selects zero rows

### Requirement: Load the private 7B runtime without downloads
The real SFT path MUST load tokenizer and model from the configured existing private `base_model_runtime_path`, require public identity and exact geometry for `Qwen/Qwen2.5-7B-Instruct`, require at least 12 GiB of local weight inventory, pass `local_files_only=true`, `trust_remote_code=false`, BF16 dtype, and `low_cpu_mem_usage`, and MUST NOT use `device_map="auto"`. It MUST propagate `bf16`, `fp16`, `tf32`, `gradient_checkpointing`, `use_cache`, `seed`, `max_steps`, `max_train_rows`, batch size, accumulation, save strategy, and logging steps into training behavior and metadata.

#### Scenario: Configure the bounded local model
- **WHEN** the ready smoke loads the Qwen2.5-7B-Instruct runtime
- **THEN** both tokenizer and model use local-only loading, the model uses BF16 and low-CPU-memory loading, Trainer/Accelerate owns placement on the one visible GPU, gradient checkpointing sets `model.config.use_cache=false`, and a missing pad token uses only a validated EOS fallback

#### Scenario: Reject unresolved local model
- **WHEN** the private model path is absent, public identity differs, local config/tokenizer cannot load, or required stable inventory cannot be produced
- **THEN** preflight returns a stable model blocker without downloading or loading model weights

### Requirement: Apply the real-training output gate to DPO
The system MUST derive DPO's repository root from the supplied manifest checkout without depending on the process working directory, fail closed when that checkout cannot be established, apply the same canonical output-root policy to DPO `--run-training` before metadata or dependency work, pass the derived root explicitly to the runner, and exclusively claim and revalidate the output directory again before imports or model loading. This defensive gate MUST NOT be interpreted as authorization to execute DPO in this change.

#### Scenario: Block a DPO output bypass
- **WHEN** DPO real mode receives a missing, escaping, symlinked, existing, or repository-local output destination
- **THEN** it returns a stable output-policy failure before dependency imports or model loading and does not write into the unsafe destination

#### Scenario: Resolve DPO policy from the manifest checkout
- **WHEN** DPO real mode is invoked from an unrelated process working directory
- **THEN** output policy still uses the repository containing the supplied manifest; if that repository cannot be resolved, execution fails closed before config, metadata, dependency, or runner work

### Requirement: Return truthful CLI exit status and one JSON result
The training CLI MUST write exactly one JSON document to stdout. Dry-run success, ready preflight, and `training_status=training_completed` MUST exit 0. Skipped-by-config, unavailable, output-policy-blocked, preflight-blocked, and runtime-exception results MUST exit non-zero. Stderr MUST NOT contain a second result JSON.

#### Scenario: Map successful results
- **WHEN** dry-run succeeds, preflight is ready, or training completes
- **THEN** the CLI emits one JSON document and exits 0

#### Scenario: Map non-success results
- **WHEN** training is skipped, unavailable, output-policy-blocked, preflight-blocked, or raises at runtime
- **THEN** the CLI emits one sanitized JSON document and exits non-zero without a competing result document on stderr
