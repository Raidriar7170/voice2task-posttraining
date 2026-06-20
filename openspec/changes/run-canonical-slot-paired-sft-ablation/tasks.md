## 1. Boundary Verification

- [x] 1.1 Locate or reconstruct control manifest `public-sample-20260617T152259Z` and treatment manifest `public-sample-20260619T090925Z` public SFT/gold inputs without mutating formal public sample files.
- [x] 1.2 Compute dev/test gold content hashes for both manifests and compare row ids, row order, and gold Browser Task Contracts.
- [x] 1.3 Write `reports/public-sample/canonical-slot-paired-sft-ablation/boundary-verification.json` with split counts, hashes, equality flags, and blocked-or-ready interpretation.
- [x] 1.4 If dev/test are not identical, write blocked `comparison.json` and `comparison.md`, recommend a shared frozen held-out set, mark runtime tasks blocked by boundary mismatch, and stop.
  - Result: not triggered; dev/test gold content, row ids, order, and contracts are identical, so the phase may proceed to paired training.

## 2. Paired SFT Runtime

- [x] 2.1 Run A100 connectivity and GPU occupancy preflight without exposing host, SSH, private path, raw log, token, or secret details in committed artifacts.
- [x] 2.2 Prepare or select paired control/treatment SFT configs using `Qwen/Qwen2.5-7B-Instruct`, the same LoRA rank, alpha, dropout, learning rate, epochs or max steps, batch size, gradient accumulation, random seed, prompt template, tokenizer, decoding parameters, evaluator, and frozen dev/test inputs.
- [x] 2.3 Train the fresh control adapter on 261 train SFT rows from `public-sample-20260617T152259Z`; do not reuse any old adapter as paired control.
- [x] 2.4 Train the fresh treatment adapter on 282 train SFT rows from `public-sample-20260619T090925Z`; do not run DPO/GRPO.
- [x] 2.5 If A100 access or safe GPU placement fails, write one blocked artifact for the phase, do not create replacement design/review/candidate evidence, and stop.
  - Result: not triggered. A100 setup initially needed project-local dependency repair and a private base-model cache, then both fresh SFT adapters completed. No DPO/GRPO run was launched.

## 3. Frozen Dev/Test Evaluation

- [x] 3.1 Generate dev/test predictions for both adapters on the exact same frozen held-out inputs using identical decoding parameters.
- [x] 3.2 Evaluate control and treatment dev/test predictions with the existing evaluator and write per-arm artifacts under `control/` and `treatment/`.
- [x] 3.3 Report primary metrics: `contract_exact_match_strict`, `slot_value_exact_f1`, `slot_value_normalized_f1`, and `executable_contract_pass_rate`.
- [x] 3.4 Report guardrail metrics: `schema_validity`, `route_accuracy`, `task_type_accuracy`, `safety_recall`, `unsafe_false_negative_rate`, `requires_confirmation_accuracy`, and `json_valid_rate`.

## 4. Comparison And Gate

- [x] 4.1 Write `comparison.json` and `comparison.md` with absolute deltas computed as Treatment minus Control, dev/test split separation, and no semantic-equivalence or repair scoring.
- [x] 4.2 Include top family-level deltas, exact recoveries/regressions, slot recoveries/regressions, and safety/confirmation regressions.
- [x] 4.3 Apply the one-seed pilot gate and recommend later three-seed confirmation only if both dev/test meet the slot, executable-pass, safety, unsafe-false-negative, and confirmation thresholds.
- [x] 4.4 If the gate fails, recommend `design-and-implement-contract-v2` and do not recommend small extra canonical candidates or DPO.
  - Result: pilot gate failed because test `slot_value_exact_f1` improved by `+0.027740`, below the `+0.03` threshold. The comparison recommends `design-and-implement-contract-v2`, not extra candidates, DPO, or 3-seed confirmation.

## 5. Public Evidence, Docs, And Validation

- [x] 5.1 Update `CONTEXT.md`, `reports/final_status.md`, and generate `docs/human-briefs/2026-06-20-run-canonical-slot-paired-sft-ablation.html` from the observed-or-blocked artifacts.
- [x] 5.2 Run focused validation for boundary verification/comparison artifacts, public dataset validation, DPO pair checks in read-only mode, and public leak scans.
  - Result: boundary/comparison `jq -e` checks passed; public dataset validation returned `ok=true` with 696 SFT rows and 2100 DPO pairs; DPO check reported 2100 pairs; report leak scan and Human Brief leak scan returned `ok=true` with 0 findings.
- [x] 5.3 Run `openspec validate --all --strict`, relevant pytest, ruff, and `git diff --check`, or record exactly why any command could not run.
  - Result: focused pytest 6 passed; full pytest 507 passed; `py_compile` passed; `openspec validate --all --strict` passed 7 items; `uv run ruff check .` passed; `git diff --check` passed.
- [x] 5.4 Run Reviewer diff review, address in-scope Must Fix items only, and leave archive/merge decisions for a later explicit closeout.
  - Result: Reviewer Must Fix required sanitized per-arm training provenance. Added `control/training_summary.json`, `treatment/training_summary.json`, training/evaluation manifest disambiguation, schema retry boundary wording, and focused artifact-shape tests. Reviewer follow-up reported no Must Fix items and Final Verdict: Pass.
