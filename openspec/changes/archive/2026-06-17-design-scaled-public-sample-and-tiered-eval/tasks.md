## 1. Evidence Inventory

- [x] 1.1 Read the current manifest, current-123 retry evidence, final status, and relevant residual/diagnosis artifacts.
- [x] 1.2 Summarize current data counts, split counts, family/task/route/safety/confirmation coverage, and strict residual pressure points.

## 2. Scaled Public-Sample Design Artifact

- [x] 2.1 Create a public-safe design report under `reports/public-sample/scaled-public-sample-and-tiered-eval-design/`.
- [x] 2.2 Include target seed-count milestone, family distribution, augmentation-depth guidance, accepted contract sketches, rejected drift sketches, and later materialization validation gates.
- [x] 2.3 Record that the phase is design-only and does not mutate seed traces, SFT/DPO rows, manifests, prompts, evaluator metrics, predictions, or private corpora.

## 3. Tiered Evaluation Design Artifact

- [x] 3.1 Define diagnostic tiers for schema/structure, task/route, safety/confirmation, slot exactness, and full-contract exactness.
- [x] 3.2 Map each tier to existing metrics or failure slices and explain how it informs future data decisions.
- [x] 3.3 Preserve strict `contract_exact_match` and strict `slot_f1` as public headline metrics; keep `slot_f1_soft` and partial matches diagnostic-only.

## 4. Status Surfaces And Human Brief

- [x] 4.1 Update `CONTEXT.md` and `reports/final_status.md` with the design-only strategic pivot and non-claim posture.
- [x] 4.2 Generate a concise Chinese Human Brief under `docs/human-briefs/`.

## 5. Validation, Review, Archive, And Integration

- [x] 5.1 Add focused tests for the design report boundaries or committed evidence.
- [x] 5.2 Run focused tests, full tests, ruff, OpenSpec strict validation, public data validation, DPO pair check, leak scan, and `git diff --check`.
- [x] 5.3 Review the diff for overclaiming, metric relaxation, private-path leakage, stale manifest boundaries, and out-of-scope data/training/evaluator changes.
- [x] 5.4 Archive the OpenSpec change, then stage/commit/push under the guarded auto-integration policy.
