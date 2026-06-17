## Context

`public-sample-20260616T165835Z` added two blocked-payment repair seed rows and four derived SFT rows, all in the train split. The latest current-manifest model evidence is prediction-only and reused the existing private SFT v3 adapter; it did not train on those new train-only rows and therefore cannot prove blocked-payment repair effectiveness.

The next useful step is not another immediate training run. The project first needs a readiness/design evidence pack that verifies the current train split, repair-row coverage, config placeholders, prior metrics, and safety boundaries are coherent enough to justify a later bounded A100 SFT retry.

## Goals / Non-Goals

**Goals:**

- Create distinct public-safe training and prediction config templates for a future current-train-split SFT retry.
- Run local SFT dry-run metadata against the current public train split.
- Record that the train split contains 118 rows, including 21 form-fill remediation / confirmation-marker rows and 4 blocked-payment repair rows.
- Bind the readiness report to the latest current-manifest prediction-only metrics.
- Recommend whether to open a later bounded A100 SFT retry phase.
- Keep all private paths, overrides, adapters, checkpoints, logs, host details, SSH details, tokens, and private corpus rows out of git.

**Non-Goals:**

- No A100 training, DPO, GRPO, prediction generation, evaluator change, prompt change, dataset mutation, slot normalization, prediction repair, or prediction replacement.
- No checkpoint, adapter, production-readiness, held-out recovery, private-corpus generalization, public full-corpus release, or live-browser benchmark claim.

## Decisions

1. Use a new runtime label for the next retry.
   - Rationale: the prior private adapter is `a100-form-fill-remediation-sft-v3`; a new retry should not overwrite or blur that evidence boundary.
   - Alternative considered: reuse the old config path. Rejected because it would make evidence provenance ambiguous.

2. Keep this phase readiness-only.
   - Rationale: blocked-payment repair rows are train-only, and current evidence still shows dev `safety_recall=0.5556`; training should be a separate A100 phase with fresh GPU preflight.
   - Alternative considered: start training immediately after current-manifest baseline. Rejected because the project needs a clear retry design and public-safe config boundary first.

3. Use strict metrics as the readiness input.
   - Rationale: `contract_exact_match`, strict `slot_f1`, route accuracy, and safety recall are the public evidence boundary.
   - Alternative considered: use `slot_f1_soft` as the main improvement signal. Rejected because it is diagnostic-only.

## Risks / Trade-offs

- Metrics may still not improve after a future retry -> this phase only authorizes a bounded attempt, not a success claim.
- The 118-row train split is still small -> report must flag overfit risk and require held-out dev/test evaluation after any future training.
- Config templates may look executable but require private overrides -> keep `private_override_required=true` and placeholder paths.
- A100 resources may be unavailable later -> future training phase must perform fresh GPU/process preflight and may fail closed.
