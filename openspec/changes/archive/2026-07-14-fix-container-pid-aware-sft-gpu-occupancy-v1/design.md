## Context

The shared SFT preflight checks aggregate GPU compute occupancy after calling CUDA APIs such as `torch.cuda.mem_get_info(0)`. In the authorized A100 container, `nvidia-smi` reports the host PID for the probe's newly-created CUDA context while Python exposes a container-local PID, so filtering only `os.getpid()` produces a false `GPU_BUSY`. The gate must require empty occupancy at its two defined sample points and sufficient free memory during the helper probe, and must never expose process identity. It does not prove continuous absence of external processes between samples.

## Goals / Non-Goals

**Goals:**

- Avoid treating the ephemeral helper's released CUDA context as persistent occupancy across host/container PID namespaces.
- Keep both occupancy samples and the helper bound to one explicit `CUDA_VISIBLE_DEVICES` selector on every repeated shared preflight.
- Fail closed on occupancy observed in either sample or on occupancy/helper probe failure.
- Preserve public facts as counts and booleans only.

**Non-Goals:**

- Relaxing the requirement for one explicit A100, at least 35 GiB total memory, two empty occupancy samples, and at least 35 GiB helper-period free memory.
- Trusting process names, usernames, GPU UUIDs, commands, or caller-provided PID mappings.
- Changing training budgets, datasets, models, clean-evaluation facts, or any evaluation path.
- Starting full training, DPO, GRPO, prediction, or evaluation.
- Claiming that sampling proves continuous absence of an external process between the two sample points.

## Decisions

### Isolate CUDA facts in an ephemeral helper process

The parent process samples aggregate compute occupancy before launching a dedicated internal helper. If any process is present, it returns `GPU_BUSY` without initializing CUDA. The helper imports torch, collects the existing availability, device, BF16, total-memory, and `mem_get_info(0)` facts, emits exactly one strict typed JSON response to its parent, and exits. A torch import failure or `cuda.is_available() == false` reports `CUDA_UNAVAILABLE`; an exception from a CUDA API reports `CUDA_PROBE_FAILED`; helper timeout, non-zero exit, malformed JSON, or protocol drift reports `GPU_OCCUPANCY_PROBE_FAILED`. Raw exception text is never serialized. Only after the helper has exited and released its CUDA context does the parent sample occupancy again. Both samples must be valid and empty. This sequence is used on every shared-preflight call, including the check immediately before model loading, so the long-lived training process does not acquire a CUDA context merely to inspect the gate.

Alternative considered: compare with `os.getpid()` or `/proc/self/status` namespace PIDs. The authorized container demonstrated that neither value matches the NVML PID, so this is not portable enough. Alternative considered: infer that the unique PID appearing after CUDA initialization belongs to the probe and cache it. That can accidentally whitelist an unrelated process observed at that instant, so no identity is inferred or cached. Alternative considered: remove the occupancy check, accept one arbitrary PID, or require a host PID namespace deployment. These either weaken the two-sample gate or are unavailable in the authorized runtime.

### Keep process identity private

The public GPU object continues to expose only `compute_process_count` and `idle_verified`. Raw occupancy output and helper protocol details never enter blockers, logs, metadata, or CLI JSON.

### Launch the helper in an isolated offline environment

The parent invokes the helper as `sys.executable -I <absolute-helper-script>` with a newly constructed allowlisted environment. It passes only the exact `CUDA_VISIBLE_DEVICES` selector, user-site isolation, offline flags, and fixed locale; it does not copy caller proxy, token, `PYTHONPATH`, `PYTHONHOME`, site-customization, or dynamic-loader injection variables. Before importing torch, the helper installs a Python audit hook that rejects real CPython socket creation plus connect, bind, address-resolution, and send audit events. The helper does not pre-create a socket, so listen, connect, connect-ex, send-to, and send-message operations cannot acquire a socket before this boundary. A blocked network event becomes only the typed `CUDA_PROBE_FAILED` result.

### Isolate dependency repair from repository behavior

Runtime dependency conflicts are repaired only in a dedicated ignored venv under the authorized project directory. No system/shared Python packages are changed, and no dependency artifact is committed.

## Risks / Trade-offs

- [An external process runs only while the helper is alive and exits before the post-sample] -> Preserve the free-memory probe inside that interval and repeat the complete pre/helper/post gate immediately before model loading. Sampling cannot prove absence between observations, but no external identity is ever trusted or whitelisted.
- [The helper emits malformed data, times out, or exits non-zero] -> Return only `GPU_OCCUPANCY_PROBE_FAILED`; do not fall back to an in-process CUDA probe.
- [The helper cannot import torch or a CUDA API raises] -> Preserve the typed distinction as `CUDA_UNAVAILABLE` or `CUDA_PROBE_FAILED`, respectively, without exception text.
- [Caller environment attempts Python/module shadowing, credential propagation, proxy access, or loader injection] -> Use isolated execution, an absolute script, a minimal environment allowlist, and the pre-import network audit hook.
- [The explicit selector changes] -> Pass the exact single selector to both occupancy samples and the helper; validate the helper's visible-device count remains one.

## Migration Plan

1. Add red regression tests for isolated helper ordering, repeat probes, external occupancy, malformed helper results, and selector propagation.
2. Implement the minimal private helper protocol and parent-side fail-closed before/after sampling.
3. Run focused and full repository verification, sync the delta spec, and archive the change.
4. Push the new PR head, deploy that exact commit to the private A100 checkout, and run shared preflight.
5. Run exactly one bounded smoke only if preflight returns exit code 0, `ready=true`, and no blockers.

Rollback is the single implementation commit; removing it restores the previous conservative false blocker and cannot start training.

## Open Questions

None. A real smoke remains conditional on all shared preflight gates.
