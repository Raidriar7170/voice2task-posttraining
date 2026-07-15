## Context

The real A100 SFT path and all bounded smoke guards already exist on the PR #3 branch. The first authorized launch completed backend work but failed the public CLI protocol because downstream progress reached stdout. The fixed branch is now pinned to `df25648d1d837d7aa4af7757b9aea68783d2a5b6`; this change is an execution-and-evidence phase, not a new training implementation or metric experiment.

The execution uses a private ignored runtime on the authorized A100 machine. Public repository artifacts may contain only sanitized hashes, counts, stable status values, and verification results. They must not contain the remote host, private absolute paths, config contents, raw training rows, raw logs, model files, adapter bytes, credentials, or connection details.

## Goals / Non-Goals

**Goals:**

- Prove the exact fixed commit is deployed cleanly without copying this uncommitted OpenSpec change into the remote checkout.
- Re-establish every immutable gate before the only authorized launch.
- Execute at most one real Qwen2.5-7B-Instruct LoRA SFT smoke using one or two current-formal-manifest `train` rows and exactly one optimizer step on one explicitly selected idle A100.
- Independently verify the process, one-document CLI protocol, training completion, measured adapter update, adapter artifacts, and absence of full base-model weights.
- Preserve private evidence remotely while recording only sanitized, reviewable evidence in Git.

**Non-Goals:**

- Prediction, evaluation, DPO, GRPO, public test, lockbox, clean-evaluation population access, or any second launch.
- Hyperparameter, prompt, decoder, evaluator, curriculum, or metric experimentation.
- Generic chat fine-tuning, skill routing, GUI action-policy learning, first-phase GRPO, or public release of the full local corpus.
- Commit, push, PR mutation, merge, archive, release, deploy to production, checkpoint publication, model-improvement claim, live-browser benchmark claim, or readiness claim.

## Decisions

### 1. The exact committed branch is the only executable source

The remote repository MUST be clean and pinned to the requested commit. The stdout fix MUST be demonstrated from that checkout before preflight. Local uncommitted OpenSpec/Human Brief files are never transferred into the runtime checkout.

Alternative considered: copy the current worktree wholesale. Rejected because it would make the execution source differ from the fixed PR head and mix derived evidence files into runtime provenance.

### 2. Gates are sequential and launch authorization is consumed once

Before launch, verify the private config is ignored, untracked, and not a symlink; the local model has the required Qwen2.5-7B-Instruct identity and stable inventory/hash; the explicitly selected single visible A100 is idle and passes the configured free-memory threshold; the fresh output leaf is not pre-created and passes identity policy; and the shared preflight exits 0 with `ready=true` and no blockers. A private launch marker and count are written before invocation. Any failed gate consumes no launch but terminates the phase; after invocation, any failure terminates the phase and the launch is never repeated.

Alternative considered: repair a failed gate or run automatically. Rejected because the authorization is for one audited attempt after a complete ready gate, not an adaptive retry loop.

### 3. The CLI process is captured as three independent evidence channels

Capture stdout, stderr, and exit code separately in the private evidence directory. Parse stdout as one complete JSON document with no prefix, suffix, or second document. Treat stderr as diagnostics only and reject any competing result JSON. Verify the result object and filesystem artifacts independently rather than trusting a single status field.

Alternative considered: redirect stderr into stdout for convenience. Rejected because it destroys the protocol boundary that this rerun is intended to validate.

### 4. Smoke completion requires all runtime and filesystem postconditions

Success requires `exit_code=0`, one stdout JSON document, no competing stderr result, `training_status=training_completed`, `smoke_status=SMOKE_COMPLETED`, one observed optimizer step, one or two training rows, a positive changed-adapter-tensor count, finite adapter tensors, non-empty adapter config and adapter weight files, and no complete base-model weights anywhere in the run tree. The final check scans the complete fresh output tree, not only the adapter directory.

Alternative considered: accept trainer completion plus saved files. Rejected because it would not prove a parameter update, numerical finiteness, CLI correctness, or absence of copied base weights.

### 5. Public evidence is derived and sanitized

OpenSpec tasks and the Human Brief record the fixed commit, stable gate names, booleans, hashes where safe, aggregate counts, result fields, validation commands, and the stop verdict. Raw private evidence remains ignored on the remote machine and is referenced to the controlling agent only, not embedded in repository files.

Alternative considered: commit raw logs for auditability. Rejected because raw logs and paths can disclose private model/runtime details and training data.

## Risks / Trade-offs

- [A gate changes after preflight] → The real runner repeats bound checks before model loading; no manual bypass is permitted.
- [Another process occupies the GPU] → Select exactly one device that is fully idle at gate time and rely on the shared repeated occupancy guard; stop on drift.
- [The output directory is created concurrently] → Require a fresh absent leaf and the existing exclusive output-claim policy; stop on identity or existence drift.
- [Training succeeds but the CLI protocol is invalid] → Treat protocol failure as total smoke failure and do not retry.
- [A partial adapter exists after failure] → Preserve it only as private failure evidence; do not relabel it as a successful smoke or a control adapter.
- [Sanitization weakens reproducibility] → Preserve the complete immutable raw evidence privately and expose stable hashes/counts/statuses publicly.

## Migration Plan

1. Validate this bounded change locally.
2. Deploy only the exact committed fixed head to the existing private remote repository and prove the checkout is clean.
3. Run the ordered read-only gates and shared preflight.
4. If and only if every gate passes, create the launch marker and execute the single authorized smoke once.
5. Verify all postconditions independently and update the OpenSpec tasks/Human Brief with sanitized evidence.
6. Stop without archive, commit, push, PR mutation, merge, release, or any additional run.

Rollback is evidence-only: repository files can be reverted locally, while any private failed output remains isolated and untracked for audit. A failed or interrupted launch is not retried under this authorization.

## Open Questions

None. Model, data split, row count, optimizer-step budget, GPU count, gate order, success criteria, privacy boundary, and prohibited actions are fixed by the request.
