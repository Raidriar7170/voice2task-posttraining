## Context

The archived `run-a100-hardened-canonical-policy-rerun` phase proved that the
current prompt code can expose hardened canonical policy flags in dry-run
metadata, but it stopped before real prediction because the required source
adapter path was absent on the A100 machine.

The latest real model metrics remain the merged slot-value held-out evaluation:
train exact 1.0, dev exact 0.5, and test exact 0.8333. This phase is a
prerequisite repair only: it restores the private adapter path needed to rerun
predictions later.

## Goals / Non-Goals

**Goals:**

- Prefer restoring or relinking an existing exact merged slot-value adapter if
  one is found under the approved remote root.
- If restoration is impossible, regenerate the adapter using
  `configs/sft-a100-merged-slot-value-heldout-rerun.json` with a private
  override.
- Keep remote writes under `<approved_remote_root>`.
- Publish sanitized evidence that records whether the adapter is available and
  how it was obtained.

**Non-Goals:**

- No prediction/eval rerun in this phase.
- No new model-quality metrics, no data changes, no evaluator changes, and no
  prompt changes.
- No public release of weights, raw logs, private override files, model cache
  paths, host details, SSH details, or private corpus rows.

## Decisions

1. **Restore before train.** A matching adapter would preserve the prior run
   exactly. If none exists, regeneration is allowed because the user explicitly
   authorized this prerequisite phase.

2. **Use the previous config and manifest.** Regeneration uses the formal
   public sample manifest `public-sample-20260615T040231Z` and the archived
   merged slot-value SFT configuration.

3. **Do not commit raw adapter details.** The evidence records only sanitized
   status, dependency versions, required file names, and claim boundaries.

4. **Stop after prerequisite evidence if training is blocked.** Dependency,
   GPU, output-root, or runtime failure must become blocked evidence rather than
   a silent rerun or a substituted adapter.

## Risks / Trade-offs

- [Risk] Regenerated adapter may not be byte-identical to the original prior
  adapter. -> Mitigation: label it as regenerated, not restored, and require
  the next prediction-only rerun to measure behavior.
- [Risk] Using a different old adapter would pollute the next metrics. ->
  Mitigation: only accept the exact target runtime path or regenerate from the
  merged slot-value config.
- [Risk] Remote dependency or cache behavior can write outside the approved
  root. -> Mitigation: use the existing approved venv and set cache/tmp
  environment variables under `<approved_remote_root>`.
