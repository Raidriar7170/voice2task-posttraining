## 1. Regression Contract

- [x] 1.1 Add red tests for helper isolation, pre/post occupancy ordering, repeated probes, and exact selector propagation.
- [x] 1.2 Add red tests that fail closed for pre-existing/post-helper occupancy, helper timeout/failure/malformed output, and never expose process identity.
- [x] 1.3 Add reviewer-requested red tests for typed CUDA failures, strict helper JSON, isolated absolute-script launch, minimal environment, direct fake-torch collection, and the pre-import network audit hook.
- [x] 1.4 Add a second-review red test that installs the real hook only in an isolated child and verifies actual socket creation, listen, connect, connect-ex, send-to, send-message, and DNS APIs cannot proceed; add cross-field protocol cases.

## 2. Minimal Implementation

- [x] 2.1 Implement the private ephemeral GPU fact helper without network access or public path/process disclosure.
- [x] 2.2 Replace in-process CUDA occupancy filtering with parent pre-sample, helper execution, and parent post-sample while preserving all existing A100/BF16/memory gates.
- [x] 2.3 Generate the required Chinese Human Brief with exact training and evaluation non-goals.
- [x] 2.4 Preserve `CUDA_UNAVAILABLE` for torch import/unavailable CUDA and `CUDA_PROBE_FAILED` for CUDA API exceptions while keeping helper process/protocol uncertainty as `GPU_OCCUPANCY_PROBE_FAILED`.
- [x] 2.5 Run the helper with `sys.executable -I`, an absolute script, a fixed minimal offline environment, and a network-denying audit hook installed before torch import.
- [x] 2.6 Block real CPython `socket.__new__` before torch import and narrow all readiness wording to the two empty occupancy samples plus helper-period free memory.

## 3. Verification And Lifecycle

- [x] 3.1 Run focused GPU/preflight tests and targeted mypy on touched Python files.
  - RED: the original helper/orchestration suite initially failed `15/15`; the strengthened post-helper sample assertion then failed `2/2`; first-review hardening initially failed `16/30`; the real-socket second review failed `2/38` before `socket.__new__` was blocked.
  - GREEN: focused GPU/preflight/A100 regression passed `241/241`; touched Ruff and `git diff --check` passed.
  - Targeted Mypy reported only the two pre-existing imported-module diagnostics in `slot_error_analysis.py:574` and `copy_backed_shadow_interface.py:357`; neither touched Python file had a diagnostic.
- [x] 3.2 Run pre-archive full pytest, ruff, strict OpenSpec validation, truth-surface checker, and `git diff --check`.
  - Pre-archive full pytest passed `1424/1428`; the four expected failures and truth-surface exit `1` were solely the repository's active-change-empty boundary. Ruff, strict validation, and `git diff --check` passed; no allowlist was added.
- [x] 3.3 Sync the delta to `supervised-contract-tuning`, archive the change, confirm active changes=0, then rerun full verification.
  - Archived at `openspec/changes/archive/2026-07-14-fix-container-pid-aware-sft-gpu-occupancy-v1`; active changes are `0`.
  - Post-archive verification: full pytest `1451 passed`; Ruff, strict OpenSpec validation, truth-surface checker, and `git diff --check` passed.
  - Exact targeted Mypy reported only the two pre-existing imported-module diagnostics in `slot_error_analysis.py:574` and `copy_backed_shadow_interface.py:357`; no touched Python file had a diagnostic.
