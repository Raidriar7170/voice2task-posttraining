## Context

The current formal public held-out baseline is
`reports/public-sample/a100-formal-public-heldout-prediction-after-a100-recovery/`
on manifest `public-sample-20260616T074315Z`. The readiness phase selected the
current public train split of 114 SFT rows, including 21 merged form-fill
remediation / confirmation-marker rows. The first SFT v3 execution phase did
not reach GPU inspection because A100 SSH connectivity timed out, and it was
archived with blocked evidence.

This retry must not assume anything from the failed preflight except that the
previous run did not execute. It must repeat SSH, GPU occupancy, approved-root,
and dependency checks before creating private overrides or launching training.

## Goals / Non-Goals

**Goals:**

- Verify A100 connectivity and select an idle GPU without disturbing other
  users.
- Run one private SFT v3 training job if placement is safe.
- Run dev/test prediction-only strict evaluation if training completes.
- Import sanitized evidence only and compare against the current strict
  baseline, not against the blocked attempt as if it had metrics.
- Archive with either observed metrics or a new blocked/failed evidence pack.

**Non-Goals:**

- No DPO, GRPO, evaluator relaxation, semantic-equivalence scoring, slot
  normalization, prediction repair, or prediction replacement.
- No public release of checkpoints, adapters, raw logs, private overrides,
  private paths, model caches, or full private corpus.
- No production-readiness or live-browser benchmark claim.

## Decisions

1. Create a new retry evidence directory instead of overwriting the blocked
   preflight directory. This preserves the audit trail.

2. Use the committed SFT v3 config templates as the public contract and place
   resolved overrides only under the approved A100 root.

3. Select exactly one safe GPU with `CUDA_VISIBLE_DEVICES`; if no GPU is safe,
   stop with blocked evidence.

4. Treat dev/test strict metrics as the only model-quality evidence. The retry
   may report `slot_f1_soft`, but only as diagnostic context.

5. If training succeeds but prediction/evaluation fails, record a failed phase
   with sanitized cause rather than substituting prior predictions or fixtures.

## Risks / Trade-offs

- SSH can regress again -> record a fresh blocked status and stop.
- GPU occupancy may be ambiguous -> stop rather than preempting other users.
- A short public-sample SFT v3 run may not improve metrics -> report observed
  partial/no recovery rather than tuning the evaluator.
- Metadata may contain private runtime paths -> sanitize before commit and run
  leak scan over all evidence.
