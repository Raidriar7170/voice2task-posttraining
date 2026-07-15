## Why

The prior authorized real one-step SFT process reached training but its CLI stdout was contaminated by downstream progress output, so it did not produce a legally auditable smoke result. Commit `df25648d1d837d7aa4af7757b9aea68783d2a5b6` contains the reviewed stdout isolation fix; this change authorizes one and only one fail-closed rerun to determine whether the bounded real A100 smoke now satisfies the complete contract.

## What Changes

- Verify the remote checkout is clean and pinned to `df25648d1d837d7aa4af7757b9aea68783d2a5b6`, including the stdout-isolation fix.
- Re-establish every private-config, local-model, explicit-idle-A100, free-memory, fresh-output, and shared-preflight gate before execution.
- Authorize exactly one real local-only Qwen2.5-7B-Instruct LoRA SFT smoke over one or two rows from the current formal manifest `train` split for exactly one optimizer step.
- Accept success only when the process, CLI protocol, training metadata, measured adapter update, adapter artifacts, and no-full-base-weight postconditions all pass together.
- Stop on the first failed gate or postcondition and never retry automatically.
- Record only sanitized execution evidence in OpenSpec and the Human Brief; keep private paths, config, raw rows, logs, adapters, model files, host details, and credentials outside Git.
- Explicitly do not run prediction, evaluation, DPO, GRPO, public test, lockbox, or clean-evaluation work, and do not merge, archive, release, deploy, or claim model improvement.

Non-goals also include generic chat fine-tuning, skill routing, GUI action-policy learning, first-phase GRPO, public release of the full local corpus, a released checkpoint, or any live-browser benchmark claim.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `supervised-contract-tuning`: Add the operational acceptance contract for a single post-fix real A100 smoke rerun, including exact launch authorization, postconditions, evidence privacy, and no-retry behavior.

## Impact

- OpenSpec and derived Human Brief receive sanitized gate and result evidence.
- The private remote runtime may create one fresh ignored output tree containing the adapter and raw execution evidence only after all preflight gates pass.
- No production code, public dataset, model weights, evaluation population, prompt/evaluator policy, or clean-evaluation truth field is changed.
- PR #3 may later receive the sanitized evidence through a separately authorized update; this change does not authorize commit, push, PR mutation, merge, or archive.
