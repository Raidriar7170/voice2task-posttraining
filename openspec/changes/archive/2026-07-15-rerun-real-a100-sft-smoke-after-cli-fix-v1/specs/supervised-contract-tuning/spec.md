## ADDED Requirements

### Requirement: Rerun one real A100 SFT smoke after the CLI stdout fix
The system MUST permit at most one real SFT launch from clean commit `df25648d1d837d7aa4af7757b9aea68783d2a5b6`, using only the local Qwen2.5-7B-Instruct runtime, one or two ordered rows from the current formal manifest `train` split, exactly one optimizer step, and one explicitly selected idle A100. The launch MUST NOT perform prediction, evaluation, DPO, GRPO, public test, lockbox, or clean-evaluation population access.

#### Scenario: Establish the executable commit
- **WHEN** the bounded rerun is prepared
- **THEN** the remote tracked checkout is clean, its HEAD equals the fixed commit, the stdout-isolation fix is present, and no local uncommitted planning artifact is deployed with it

#### Scenario: Reject execution outside the fixed scope
- **WHEN** model identity, split, selected row count, optimizer-step budget, visible GPU count, or requested action differs from the authorized values
- **THEN** the system stops before launch and does not substitute another model, dataset, budget, GPU arrangement, or action

### Requirement: Re-establish every real-smoke gate before launch
Before the launch, the system MUST prove that the private config is ignored, untracked, and not a symlink; the local model identity and inventory/hash match Qwen2.5-7B-Instruct; exactly one explicitly selected A100 is visible, fully idle, and passes the configured free-memory gate; the requested output leaf is fresh, absent, and passes the bound output-identity policy; and the shared preflight exits 0 with `ready=true`, no blockers, and the exact bounded configuration. A launch marker and launch count MUST make the single authorization auditable.

#### Scenario: All gates pass
- **WHEN** every config, model, GPU, output, Git, dependency, data, objective, and shared-preflight condition passes
- **THEN** the system records the one authorized launch marker and invokes the real SFT process once

#### Scenario: Any gate fails
- **WHEN** any required gate is false, unavailable, inconsistent, or changes before invocation
- **THEN** the system records the stable blocker, performs no training launch, and stops without automatic repair, fallback, or retry

### Requirement: Accept smoke success only from the complete evidence conjunction
The run MUST be successful only when all of the following are independently true: process exit code is 0; stdout is exactly one complete JSON document; stderr contains no competing result JSON; `training_status=training_completed`; `smoke_status=SMOKE_COMPLETED`; `observed_optimizer_steps=1`; `training_rows_used` is 1 or 2; `changed_adapter_tensor_count>0`; `all_adapter_tensors_finite=true`; adapter configuration and adapter weights exist and are non-empty; and the complete run tree contains no full base-model weight file or full base-model weight inventory.

#### Scenario: Complete success evidence
- **WHEN** the single process returns and every process, protocol, metadata, update, artifact, and no-base-weight postcondition passes
- **THEN** the bounded change records the result as a completed real one-step infrastructure smoke with sanitized evidence

#### Scenario: Any postcondition fails
- **WHEN** the process is non-zero, stdout is not one JSON document, stderr contains a competing result, any required field is absent or wrong, the adapter update/artifact evidence is insufficient, or the run tree contains full base-model weights
- **THEN** the bounded change records the exact failed postcondition, does not report smoke success, and stops without a second launch

### Requirement: Keep real-smoke evidence private and claims narrow
Raw config, private paths, host details, raw selected rows, logs, cache, local model files, and adapter artifacts MUST remain in ignored private storage. Repository evidence MUST be limited to sanitized commit identity, stable hashes and counts, gate outcomes, result fields, validation results, and the truthful stop verdict. Smoke success MUST NOT change any clean-evaluation truth field or imply model quality, held-out gain, generalization gain, production readiness, released weights, or live-browser benchmark improvement.

#### Scenario: Record sanitized success or blocker evidence
- **WHEN** the phase stops after a gate or after the single launch
- **THEN** OpenSpec and the Human Brief contain enough sanitized evidence to audit the decision without disclosing private runtime values or training content

#### Scenario: Preserve lifecycle and claim boundaries
- **WHEN** the execution evidence is ready for human review
- **THEN** the system leaves the change active, does not commit, push, mutate or merge PR #3, and does not archive, release, deploy, run metric experiments, or make a model-improvement/readiness claim
