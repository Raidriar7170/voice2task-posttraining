## 1. OpenSpec and Truth Surface

- [x] 1.1 Create the `design-and-evaluate-contract-v2-projection` proposal, design, spec deltas, and task list.
- [x] 1.2 Validate the OpenSpec change in strict mode before implementation.
- [x] 1.3 Refresh README.md, README_en.md, and CONTEXT.md current status / current snapshot so the latest step-matched canonical-slot SFT ablation is current and older 77-seed / 231-SFT / 661-DPO metrics are historical.

## 2. Test-First Projection Contracts

- [ ] 2.1 Add failing tests for V1-to-V2 Core projection, V2 Core validation, canonical JSON determinism, envelope metadata, and renderer determinism.
- [ ] 2.2 Add failing tests that the renderer ignores old `normalized_command`, fails closed for unsupported cases, preserves distinct slot values, and retains safety/confirmation fields.
- [ ] 2.3 Add failing tests for V2 core executable pass unsafe-downgrade handling, failure contribution categories, report completeness, and public leak-scan boundaries.

## 3. Projection and Evaluation Implementation

- [ ] 3.1 Add experimental `src/voice2task/contract_v2_projection.py` with pure deterministic projection, validation, canonicalization, envelope, and renderer functions.
- [ ] 3.2 Add offline projection evaluator/report generation that discovers latest committed step-matched artifacts, aligns Control/Treatment dev/test rows by stable sample id, and writes a blocked artifact on missing or unalignable inputs.
- [ ] 3.3 Compute L0/L1/L2/L3 metrics, original metric carry-forward, V2 executable pass, renderer coverage, deterministic roundtrip, failure contribution analysis, family deltas, and fixed-seed bootstrap diagnostics.
- [ ] 3.4 Add or wire a CLI/report command that generates all required `reports/public-sample/contract-v2-projection/` artifacts without model, network, A100, SSH, or prediction dependencies.

## 4. Evidence, Brief, and Validation

- [x] 4.1 Generate the Contract V2 projection report artifacts under `reports/public-sample/contract-v2-projection/`.
- [x] 4.2 Generate `docs/human-briefs/2026-06-20-design-and-evaluate-contract-v2-projection.html`.
- [x] 4.3 Run `PYTHONPATH=src pytest -q`.
- [x] 4.4 Run `PYTHONPATH=src ruff check src tests`.
- [x] 4.5 Run `OPENSPEC_TELEMETRY=0 openspec validate --all --strict`.
- [x] 4.6 Run `git diff --check` and a public leak scan.
- [x] 4.7 Run a read-only Reviewer pass over the diff, fix in-scope Must Fix findings only, then stop without starting Contract V2 implementation, training, DPO, data expansion, or challenge-set work.
