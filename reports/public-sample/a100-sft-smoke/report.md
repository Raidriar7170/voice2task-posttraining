# A100 Public-Sample SFT Smoke Evidence

Status: completed. The initial Hugging Face download path was unavailable, then the same `Qwen/Qwen2.5-0.5B-Instruct` model ID was fetched through ModelScope into a private remote local snapshot and the bounded A100 public-sample SFT smoke completed.

This evidence pack is for a bounded public-sample SFT smoke. It is not a checkpoint release and makes no live-browser benchmark improvement claim.

## Scope

- Base model: `Qwen/Qwen2.5-0.5B-Instruct`
- Model source: `modelscope`
- Model cache policy: `private_remote_model_cache_not_copied_to_git`
- Dataset manifest: `public-sample-20260601T162313Z`
- Training command shape: `voice2task-train sft --run-training` with `configs/sft-a100-public-smoke.json`
- Output placement: `<a100_run_dir>` under `<a100_project_root>`
- Training status: `training_completed`
- Release status: `not_released`

## Public Boundary

- Raw logs copied to git: no
- Checkpoints or adapters copied to git: no
- Remote caches copied to git: no
- Public model predictions copied to git: no
- Hostnames, private addresses, account-specific access details, tokens, raw private rows, and remote model cache paths: omitted

## Evidence Captured

- Sanitized adapter metadata with package versions, dataset manifest ID, output placement placeholders, command summary, ModelScope source label, and private cache policy
- Aggregate contract metrics link for the committed public sample
- Controlled smoke status: not run for the trained A100 model path because no public model predictions were copied back
- Leak-scan result for this public evidence pack

## Boundary

This completed smoke proves the configured Transformers + PEFT + TRL SFT training path can execute once on the public sample in the A100 environment. It does not prove model quality, does not publish an adapter, and does not support a live-browser benchmark improvement claim.
