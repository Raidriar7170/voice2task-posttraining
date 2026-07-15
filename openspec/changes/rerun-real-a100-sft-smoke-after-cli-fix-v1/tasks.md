## 1. Bounded Change and Source Identity

- [x] 1.1 Confirm the isolated local worktree is clean at `df25648d1d837d7aa4af7757b9aea68783d2a5b6` before creating this change
- [x] 1.2 Create proposal, design, delta spec, task checklist, and the initial Chinese Human Brief with the one-launch, no-retry, privacy, and prohibited-action boundaries
- [x] 1.3 Validate the change artifacts strictly before any remote deployment or preflight
  - Fresh `openspec validate rerun-real-a100-sft-smoke-after-cli-fix-v1 --strict`: passed.

## 2. Exact Remote Deployment and Ordered Gates

- [x] 2.1 Deploy only committed head `df25648d1d837d7aa4af7757b9aea68783d2a5b6` to the existing private runtime repository; prove remote HEAD and tracked cleanliness without copying local uncommitted artifacts
  - Normal fetch did not complete; a verified 39 KiB incremental Git bundle containing only the committed branch delta from the already present base was used. Remote HEAD equals the fixed commit and tracked change count is zero.
- [x] 2.2 Prove the CLI stdout-isolation fix is present and the private config is ignored, untracked, and not a symlink
  - The fixed checkout contains both the stdout redirect and diagnostic-prefix markers. Private config facts are `git_ignored=true`, `git_tracked=false`, `nonsymlink=true`, with mode `0600`.
- [x] 2.3 Prove the local-only Qwen2.5-7B-Instruct identity/inventory hash, select exactly one fully idle A100 explicitly, and pass its free-memory gate
  - Model public identity is `Qwen/Qwen2.5-7B-Instruct`; geometry matches, local-only mode is true, snapshot revision SHA-256 is `2a1aaaf30e79bc9817f385e41260f822b4533f570a62f7253afc536e8f724363`, and weight inventory totals 15,231,271,888 bytes. One A100-SXM4-80GB was selected explicitly with zero compute processes and 78.734 GiB free against the 35 GiB threshold.
- [x] 2.4 Prove the fresh output leaf is absent and passes output identity policy, then run the shared preflight once and require exit 0, `ready=true`, no blockers, the current formal manifest `train` split, one or two rows, and exactly one optimizer step
  - The output leaf was absent and its root was an absolute existing non-symlink directory. Shared preflight exited 0 with exactly one stdout JSON document, empty stderr, `ready=true`, `blockers=[]`, output ready, current formal manifest `public-sample-20260619T090925Z` / `train`, 2 selected rows, and `max_steps=1`.

## 3. Single Authorized Smoke and Independent Verification

- [x] 3.1 If and only if every gate passes, write the private launch marker/count and invoke the real SFT smoke exactly once; otherwise record the blocker and stop
  - The private atomic launch marker records `attempt=1`; the phase launch-directory count is exactly 1 and no second invocation occurred.
- [x] 3.2 Capture stdout, stderr, and exit code independently; prove exit 0, stdout is exactly one JSON document, and stderr has no competing result JSON
  - Exit code is 0. Stdout is 6,758 bytes and parses in full as exactly one JSON document. Stderr is 1,573 bytes; whole-document and line-level JSON parsing found zero JSON documents, and result-field scans found no competing result.
- [x] 3.3 Prove `training_status=training_completed`, `smoke_status=SMOKE_COMPLETED`, `observed_optimizer_steps=1`, `training_rows_used` is 1 or 2, `changed_adapter_tensor_count>0`, and `all_adapter_tensors_finite=true`
  - Observed values are `training_completed`, `SMOKE_COMPLETED`, 1 optimizer step, 2 rows, 112 changed adapter tensors out of 224, and all adapter tensors finite. Before/after adapter digests differ.
- [x] 3.4 Prove non-empty adapter configuration and adapter weights exist, scan the whole run tree for absence of full base-model weights, and prove this phase recorded only one launch
  - The adapter config is 1,029 bytes and the adapter safetensors file is 20,214,760 bytes. The full run tree contains 4 files totaling 20,234,578 bytes; exact base-shard matches and suspicious full-weight files are both zero. Launch count remains 1.

## 4. Sanitized Evidence and Validation

- [x] 4.1 Keep raw logs, paths, config, rows, cache, model files, and adapter artifacts private; update OpenSpec and the Human Brief only with sanitized gate/result evidence and the truthful completed-or-blocked verdict
  - Repository evidence contains only public commit/model/dataset identities, hashes, aggregate counts, status fields, and validation results. Raw runtime evidence and adapter files remain ignored/private on the authorized machine.
- [x] 4.2 Run focused CLI/preflight regression tests for the fixed stdout and smoke contract
  - Fresh focused result: `206 passed` across the review-hardening, private-preflight, and A100 SFT smoke modules.
- [x] 4.3 Run fresh public dataset-builder, schema-metric, and DPO-pair contract checks only through their existing no-training test entry points; record them as N/A only if the repository exposes no applicable entry point for this evidence-only change
  - Fresh no-training contract result: `30 passed` across `test_dataset_builder.py`, `test_schemas.py`, and `test_dpo_validation.py`.
- [x] 4.4 Run the existing public-leak/ignore checks, `openspec validate --all --strict`, and `git diff --check`; report `git status --short`
  - Leak scan of this change and Human Brief passed with zero findings; remote ignore/untracked/non-symlink checks passed; strict OpenSpec validation passed 16/16; `git diff --check` passed. Status contains only the new Human Brief and new bounded change as untracked paths.
- [x] 4.5 Stop with the OpenSpec change active and without archive, commit, push, PR mutation, merge, release, deploy, prediction, evaluation, DPO, GRPO, test/lockbox access, clean-evaluation work, or a model-improvement/readiness claim
  - The change remains active. No protected integration or prohibited execution occurred; forbidden claim-marker scan passed.
