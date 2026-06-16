## Context

The formal public sample was just rebuilt with 9 reviewed `form_fill` remediation candidates. The committed held-out prediction evidence under `reports/public-sample/a100-formal-public-heldout-prediction/` predates that merge, so its metrics are no longer tied to the current manifest boundary. The existing dev/test prediction configs already reference the updated public manifest id and require a private A100 override for runtime paths.

## Goals / Non-Goals

**Goals:**

- Run prediction-only dev/test evaluation against the current formal public sample manifest.
- Commit only sanitized public evidence: predictions, metrics, diagnostics, sidecars, manifests, Markdown reports, and Human Brief.
- Record manifest id, split counts, execution scope, and residual families so later phases can decide whether form-fill remediation helped.
- Keep strict `contract_exact_match`, strict `slot_f1`, and the contract evaluation ladder authoritative.

**Non-Goals:**

- No SFT, DPO, GRPO, or other training.
- No evaluator metric change, semantic-equivalence scoring, prediction repair, prediction replacement, or prediction re-score.
- No checkpoint or adapter release.
- No production readiness, held-out recovery, live-browser benchmark improvement, public full-corpus release, or private-corpus generalization claim.

## Decisions

- Use the existing prediction-only runtime path and configs rather than adding a new training or evaluator path.
  - Rationale: the next evidence question is whether the already-trained private adapter behaves differently against the new formal manifest boundary.
  - Alternative considered: retrain after adding the candidates. Rejected for this phase because it would conflate data merge effects with training effects.

- Execute on the authorized A100 development machine only after checking GPU/process occupancy.
  - Rationale: 7B prediction is GPU-heavy and the base model/adapter are already on the A100 machine.
  - Alternative considered: local Mac prediction. Rejected because it is too slow and does not match existing evidence runtime.

- Commit sanitized output artifacts only.
  - Rationale: configs intentionally require private override paths; raw logs, adapter paths, host details, caches, and private runtime paths must stay out of git.
  - Alternative considered: committing raw run logs for reproducibility. Rejected because they can expose private infrastructure and are not needed for public evidence.

## Risks / Trade-offs

- Private adapter or A100 runtime may be unavailable -> record a blocked evidence status rather than fabricating predictions.
- GPU occupancy may be unsafe -> stop before launching the run and preserve the blocked state.
- Metrics may not improve -> report observed strict metrics and residual families without overclaiming.
- Prediction artifacts may include path-like or private details -> run leak scans before commit and keep only sanitized artifacts.
