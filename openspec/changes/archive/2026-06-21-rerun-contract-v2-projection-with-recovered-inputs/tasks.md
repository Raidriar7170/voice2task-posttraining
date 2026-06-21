## 1. OpenSpec and Boundary Planning

- [x] 1.1 Create proposal, design, spec deltas, and task list for `rerun-contract-v2-projection-with-recovered-inputs`.
- [x] 1.2 Validate the new OpenSpec change in strict mode before implementation.
- [x] 1.3 Confirm previous `recover-step-matched-projection-inputs` is complete and archive-ready without archiving it inside this bounded rerun.

## 2. Test-First Projection Rerun Coverage

- [x] 2.1 Add failing tests for V2 Core projection, validation, canonical JSON, envelope metadata, and renderer determinism.
- [x] 2.2 Add failing tests for renderer ignoring old `normalized_command`, unsupported fail-closed behavior, distinct value preservation, and safety/confirmation retention.
- [x] 2.3 Add failing tests for recovered source-boundary validation, parsed-contract input use, no historical evidence overwrite, report completeness, and public leak safety.
- [x] 2.4 Add failing tests for V1 evaluator semantics remaining unchanged, failure contribution categories, fixed-seed bootstrap, and V2 executable pass criteria.

## 3. Projection and Report Implementation

- [x] 3.1 Implement or reuse pure deterministic projection helpers: `project_v1_to_v2_core`, `validate_v2_core`, `canonical_v2_core_json`, `build_v2_envelope`, and `deterministic_normalized_command_renderer`.
- [x] 3.2 Implement recovered-input boundary validation that reads only `reports/public-sample/step-matched-canonical-slot-ablation/raw-inputs/`.
- [x] 3.3 Implement the rerun report command that writes all required artifacts under `reports/public-sample/contract-v2-projection/rerun-with-recovered-inputs/`.
- [x] 3.4 Compute original metrics, projection ladder metrics, V2 executable pass, failure contributions, family deltas, fixed-seed bootstrap, renderer coverage, decision label, and recommended next change.

## 4. Evidence, Docs, Review, and Validation

- [x] 4.1 Generate the recovered-input projection rerun evidence bundle.
- [x] 4.2 Update README.md, README_en.md, and CONTEXT.md with a concise current snapshot and non-claims.
- [x] 4.3 Generate `docs/human-briefs/2026-06-21-rerun-contract-v2-projection-with-recovered-inputs.html`.
- [x] 4.4 Run `PYTHONPATH=src pytest -q`.
- [x] 4.5 Run `PYTHONPATH=src ruff check src tests`.
- [x] 4.6 Run `OPENSPEC_TELEMETRY=0 openspec validate --all --strict`.
- [x] 4.7 Run `git diff --check` and a public leak scan over new artifacts.
- [x] 4.8 Run a read-only Reviewer pass over the diff, fix in-scope Must Fix items only, then stop without starting Contract V2 implementation, training, DPO, data expansion, or challenge-set work.
