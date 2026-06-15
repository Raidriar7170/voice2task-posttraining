## 1. Proposal And Configs

- [x] 1.1 Confirm the phase is prediction-only and reuses the existing merged
  slot-value 7B adapter.
- [x] 1.2 Add train/dev/test hardened canonical policy prediction configs with
  placeholders and no training opt-in.
- [x] 1.3 Add focused tests for config boundaries and public-safety scanning.

## 2. Evidence Writer And Local Validation

- [x] 2.1 Add a hardened canonical policy rerun report CLI/writer that can
  produce either observed metrics evidence or blocked status.
- [x] 2.2 Add focused tests for strict metric comparison, prompt-flag
  provenance, claim boundaries, and sanitized paths.
- [x] 2.3 Run public sample validation, focused tests, full tests as feasible,
  OpenSpec validation, leak scan, and `git diff --check`.

## 3. A100 Prediction/Evaluation

- [x] 3.1 Check SSH, approved remote root, dependency environment, and GPU
  occupancy before launching.
- [x] 3.2 Sync current source/configs to the approved A100 project root without
  committing private overrides or logs.
- [x] 3.3 If safe, run train/dev/test prediction-only exports and strict
  metrics; otherwise write blocked evidence.
- [x] 3.4 Import only sanitized observed metadata/metrics when available; for
  the blocked path, record that observed split metadata is unavailable because
  the required source adapter is missing.

## 4. Review, Brief, Archive

- [x] 4.1 Generate the Chinese Human Brief for this phase.
- [x] 4.2 Run Reviewer pass and fix in-scope Must Fix items only.
- [x] 4.3 Archive the OpenSpec change after validation passes.
- [x] 4.4 Guarded stage and commit under `/opsx auto` integration policy.
