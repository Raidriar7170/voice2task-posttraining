## Why

The bootstrap phase proves the public-sample SFT/DPO pipeline in dry-run mode, but it still has no evidence that the real TRL/PEFT SFT path can execute on the A100 environment. This change adds one tightly bounded public-sample SFT smoke run so the project can move from runnable scaffolding to a real, sanitized training evidence pack without expanding into full private-corpus training.

## What Changes

- Add an opt-in A100 public-sample SFT smoke workflow that uses the existing Qwen-family LoRA SFT path with explicit remote output placement under `<a100_project_root>`.
- Add smoke-run configuration and launch/evidence commands that avoid secrets, host details, private IPs, raw private rows, and checkpoint publication claims.
- Export sanitized adapter metadata, run manifest, command transcript summary, and contract-level evaluation artifacts for the public sample.
- Add validation and leak-scan coverage for the A100 evidence pack.
- Keep heavy training opt-in: no model download or training starts without explicit `--run-training` plus `allow_heavy_training: true`.
- Non-goals: generic chat fine-tuning, Hermes-style skill routing, GUI action policy learning, first-phase GRPO/rule-reward training, publishing the full local/private corpus, publishing model checkpoints, or claiming live-browser benchmark improvement before controlled evidence exists.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `supervised-contract-tuning`: require a bounded, opt-in A100 public-sample SFT smoke run path with sanitized run metadata and no released-checkpoint claim.
- `contract-evaluation`: require a public-safe evidence summary for the A100 SFT smoke run, including contract metrics, controlled smoke status, and leak-scan results.

## Impact

- Affects SFT config templates, training metadata export, report/evidence generation, README or runbook documentation, and tests around training/evidence validation.
- Uses the existing Transformers + PEFT + TRL stack; dependency expansion should be avoided unless the real SFT smoke exposes a concrete missing dependency.
- Requires A100 execution for the apply phase, but all generated remote files must remain under the approved private A100 project root and only sanitized summaries may be copied into the repo.
