## Why

The shared A100 preflight currently compares NVML host PIDs with the container-local `os.getpid()`. After the probe creates its own CUDA context, that namespace mismatch can misclassify the probe itself as an external compute process and block a GPU whose required pre-probe occupancy sample was empty with `GPU_BUSY`.

## What Changes

- Avoid a host/container PID comparison by collecting CUDA facts in an ephemeral helper between two occupancy samples on the explicitly selected GPU.
- Require both occupancy samples to be valid and empty, and require the helper-period free-memory threshold; fail closed when any observed sample or probe fails.
- Keep PIDs and all other process identity details out of public preflight facts and CLI output.
- Add regression coverage for repeated preflight, external occupancy, ambiguous races, and GPU-selection isolation.
- Keep all existing A100, BF16, total/free-memory, explicit-selection, and real-smoke gates unchanged.
- Do not claim continuous absence of external processes between the two occupancy samples; the contract is the two samples plus helper-period free memory.
- Do not run full training, DPO, GRPO, prediction, evaluation, or make model-improvement claims.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `supervised-contract-tuning`: Strengthen the shared SFT GPU occupancy contract for container PID namespaces while preserving fail-closed external occupancy detection.

## Impact

- Affected implementation: `src/voice2task/training.py` shared SFT GPU preflight.
- Affected tests: private A100 preflight and review-hardening GPU occupancy tests.
- Affected specification: `supervised-contract-tuning`.
- No public API expansion, dependency change, dataset change, or evaluation-readiness change.
