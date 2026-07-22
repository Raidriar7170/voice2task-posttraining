## MODIFIED Requirements

### Requirement: Provide one shared SFT preflight
The system MUST expose `sft-preflight` and MUST use the same internal preflight core from real SFT execution before loading model weights. That core MUST produce the public report plus an immutable private execution context binding canonical inputs, selected rows, model inventory, and output facts. Real training MUST consume the bound context rather than reselecting data from caller arguments and MUST rehash mutable inputs before model loading. The single public JSON result MUST use schema `voice2task-sft-preflight-v1`, report `ready`, `status`, `blockers`, and the `git`, `config`, `dataset`, `model`, `runtime`, `gpu`, `output`, and `objective` sections, and MUST not access the network. In a container PID namespace, the GPU hardware probe MUST run in an ephemeral helper process between two parent occupancy samples so the helper releases its own CUDA context before the second sample; both parent samples MUST be valid and contain zero compute processes, the helper-period free-memory threshold MUST pass, and the system MUST NOT infer or serialize any process identity. This sampling contract MUST NOT be represented as proof that no external process existed continuously between the two samples.

#### Scenario: Report a ready bounded smoke
- **WHEN** Git tracked state is clean and includes the change, the ignored non-symlink private config is exactly smoke-bounded, dependencies and `pip check` pass, one explicit BF16-capable A100 has at least 35 GiB total memory, both defined occupancy samples contain zero compute processes, the helper observes at least 35 GiB free memory, exact local Qwen2.5-7B model/tokenizer identity and >=12 GiB weight inventory pass, selected formal train rows and assistant-only labels pass, and output policy passes
- **THEN** preflight returns exit code 0 with `ready=true`, an empty blocker list, stable fingerprints, hashes, versions, counts, and public-safe facts

#### Scenario: Isolate the probe context across PID namespaces
- **WHEN** the selected GPU has no compute process before the helper starts, the helper successfully collects CUDA facts and exits, and the selected GPU again has no compute process after the helper exits
- **THEN** the shared probe reports `compute_process_count=0` and `idle_verified=true` without comparing, inferring, caching, or emitting any PID

#### Scenario: Preserve typed CUDA failures and fail closed on helper uncertainty
- **WHEN** occupancy exists in either parent sample, an occupancy sample fails, torch cannot be imported, a CUDA API raises, or the helper times out, exits non-zero, or emits an invalid result
- **THEN** preflight returns non-zero with `GPU_BUSY` for confirmed occupancy, `CUDA_UNAVAILABLE` for torch import or unavailable CUDA, `CUDA_PROBE_FAILED` for a CUDA API failure, or `GPU_OCCUPANCY_PROBE_FAILED` for occupancy/helper process or protocol uncertainty, without exposing process identities or raw error text

#### Scenario: Isolate the helper from caller environment and network
- **WHEN** the parent starts the ephemeral CUDA helper
- **THEN** it uses `sys.executable -I` with the absolute helper script and a new allowlisted environment containing only the exact selector, user-site isolation, offline flags, and fixed locale, and before importing torch the socket-free helper installs a Python audit hook that blocks real socket creation and network audit events

#### Scenario: Report blocked readiness safely
- **WHEN** any required Git, config, dependency, GPU, model, dataset, objective, or output condition fails
- **THEN** preflight returns non-zero with `ready=false` and only stable enumerated blocker codes, including `GPU_FREE_MEMORY_INSUFFICIENT`, `GPU_BUSY`, or `GPU_OCCUPANCY_PROBE_FAILED` for the corresponding GPU state, without raw exceptions or private runtime values

#### Scenario: Fail closed on an unexpected preflight exception
- **WHEN** any internal shared-preflight operation raises an unexpected exception
- **THEN** both `sft-preflight` and real SFT return the complete blocked preflight schema with only `PREFLIGHT_INTERNAL_ERROR`, do not serialize exception text or private values, and do not write the candidate output

#### Scenario: Consume only the bound ready context
- **WHEN** real SFT reaches a ready shared preflight result
- **THEN** it builds execution metadata only from the bound report and immutable context, without rereading legacy config, manifest, or dataset inputs around the gate, and binds the exact model facts produced by the validated model probe
