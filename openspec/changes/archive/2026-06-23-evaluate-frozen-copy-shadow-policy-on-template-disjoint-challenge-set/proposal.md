## Why

The current copy-backed shadow evidence proves the frozen policy and prediction hook on recovered dev/test artifacts and a small public fixture, but it does not prove behavior on templates that were not used for scope selection, policy design, verifier design, model training, or dev/test debugging.

This change evaluates the frozen `copy-backed-scope-policy-v1` on a public-safe template-disjoint challenge set to decide whether observe-only shadow use can continue, while preserving the no-training, no-enforcement, no-policy-mutation boundary.

## What Changes

- Harden the existing prediction shadow hook before challenge materialization:
  - reject non-default no-op retention/fail-isolation config values;
  - load and validate the frozen policy once per prediction run;
  - detect policy drift across the run;
  - isolate sidecar path conflicts from primary prediction output.
- Materialize and freeze `copy-shadow-template-disjoint-challenge-v1` as public-safe challenge data outside the current train/dev/test split.
- Audit the challenge set for sample id, exact input, template signature, slot-value-stripped signature, 3-gram similarity, edit similarity, public safety, gold-contract validity, and gold-verifier feasibility.
- Run challenge prediction through the canonical `voice2task-train sft-predict` / `run_sft_prediction_export` hook path when verifiable frozen adapter outputs are available; otherwise write a blocked artifact and stop.
- Generate gold-free online sidecars, separate offline evaluation audits, per-scope metrics, per-condition metrics, latency evidence, privacy audit, policy-freeze audit, and a bounded final decision.
- Update README/CONTEXT/evidence index and add a concise Chinese Human Brief.
- Archive the OpenSpec change after full verification.

No breaking API change is intended. The hook remains default-off and observe-only.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `copy-backed-verification-shadow-mode`: add requirements for template-disjoint challenge evaluation, run-level policy freeze, path conflict isolation, challenge manifest freezing, canonical prediction hook evaluation, privacy/latency/policy audits, and bounded decision labels.

## Impact

- Affected code:
  - `src/voice2task/copy_backed_prediction_shadow_hook.py`
  - `src/voice2task/copy_backed_shadow_interface.py`
  - `src/voice2task/training.py`
  - challenge/evaluation/report scripts under `scripts/`
  - focused tests under `tests/`
- Affected artifacts:
  - `data/public-samples/copy-shadow-template-disjoint-challenge-v1.jsonl`
  - `reports/public-sample/copy-shadow-template-disjoint-challenge-v1/`
  - `docs/copy-shadow-template-disjoint-challenge.md`
  - `docs/human-briefs/`
  - README/CONTEXT/evidence index
- Explicit non-goals:
  - no SFT, DPO, GRPO, model retraining, adapter modification, prompt change, decoding change, policy change, enabled-triple change, evaluator change, layered-evaluator change, prediction repair, gold repair, action enablement, normalized trusted provenance, runtime enforcement, production/safety readiness claim, live-browser benchmark claim, checkpoint release, adapter release, or merge of challenge rows into train/dev/test.
