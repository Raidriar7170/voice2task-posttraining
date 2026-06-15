## Context

The previous archived phase produced:

- `data/public-samples/slot_value_generalization_seed_candidates.jsonl`: 4 candidate seed rows.
- `reports/public-sample/slot-value-generalization-materialized-candidates/sft_candidate_rows.jsonl`: 12 candidate SFT rows.
- A manifest stating `public_sample_modified=false`, `training_run=false`, `prediction_run=false`, and `dpo_run=false`.

The next approved direction is B: keep the formal public sample unchanged and run a smaller candidate-set probe first. Local Mac validation lacks train/prediction dependencies, while A100 preflight can connect to the `volcano` alias and found idle GPUs, but default remote Python lacks `trl` and `datasets`. Therefore this phase must distinguish executable prep evidence from real SFT completion.

## Goals / Non-Goals

**Goals:**

- Create a candidate-only manifest for the 12 materialized SFT rows.
- Create public-safe 7B A100 SFT and prediction templates for the candidate probe.
- Use local dry-run metadata to prove the training path selects exactly the candidate rows.
- Record A100 preflight/dependency status without leaking private host/path details into committed artifacts.
- Keep all claims bounded to candidate-only learning-signal readiness unless a real A100 run later completes.

**Non-Goals:**

- No formal public sample mutation.
- No DPO, GRPO, evaluator relaxation, or release claim.
- No claim that candidate rows improve held-out dev/test strict exact.
- No committed raw remote logs or private runtime paths.

## Decisions

1. Use a separate candidate manifest instead of the formal public sample manifest.
   - Rationale: `run_sft` already supports arbitrary manifests with `files.sft`, so a separate manifest lets the probe reuse training code without rewriting the public sample.
   - Alternative considered: append candidates into `seed_traces.jsonl` and rebuild the formal sample. Rejected because the user chose B and because that would change the training-data surface.

2. Mark the probe as overfit/learning-signal, not held-out generalization.
   - Rationale: training/prediction on the 12 candidate rows can only show candidate-row memorization or objective-path behavior.
   - Alternative considered: immediately predict dev/test after training. Deferred because it changes the success standard beyond candidate learning signal.

3. Commit only public-safe prep/dry-run evidence unless the real A100 run produces sanitized outputs.
   - Rationale: A100 dependency state is currently not sufficient in the default remote Python environment; blocked status is a valid evidence outcome.
   - Alternative considered: install dependencies automatically. Deferred unless a focused remote setup phase is explicitly selected, because environment mutation can take time and should be tracked separately.

4. Keep configs as templates with `<a100_project_root>` placeholders.
   - Rationale: committed configs must not expose private remote paths; private overrides belong outside git on A100.

## Risks / Trade-offs

- **Risk:** Dry-run evidence is mistaken for training evidence.
  **Mitigation:** report `training_run=false` and use `training_status=dry_run` unless a real A100 execution completes.
- **Risk:** Candidate probe overfit is retold as held-out recovery.
  **Mitigation:** manifest/report/Human Brief explicitly say `held_out_generalization_recovered=false`.
- **Risk:** A100 dependency blockage gets smoothed over.
  **Mitigation:** record sanitized dependency status and block reason.
- **Risk:** Future merge decision becomes implicit.
  **Mitigation:** stop after candidate-only probe prep/blocked evidence before formal sample merge or dev/test rerun.

## Migration Plan

1. Add RED tests for candidate manifest/config/report boundaries.
2. Implement report writer and CLI command for candidate probe evidence.
3. Generate candidate manifest, configs, dry-run metadata, and evidence report.
4. Optionally sync and execute on A100 only if dependency/output-root checks are safe; otherwise record blocked status.
5. Generate Human Brief, validate, archive, and commit.

Rollback is deleting the candidate probe manifest/config/evidence files and archived change. Existing formal public sample data remains untouched.

## Open Questions

- Whether to run a separate remote environment setup phase to install missing A100 training dependencies.
- Whether successful candidate-row overfit should be followed by formal public sample merge or a dev/test prediction-only rerun.
