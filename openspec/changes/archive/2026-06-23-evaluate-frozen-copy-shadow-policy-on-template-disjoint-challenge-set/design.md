## Context

The current copy-backed verifier line has completed task-scoped verification, offline shadow replay, an online sidecar/offline audit split, and a default-off prediction hook. The current hook decision is `PREDICTION_SHADOW_HOOK_READY_OBSERVE_ONLY`; the only recommended next change is this template-disjoint challenge evaluation.

The challenge must use frozen `copy-backed-scope-policy-v1` with policy hash `5dc14efb8ded13dc048ddb067c7c63a1a62b6c03896950e861303973d505cbc7`. It must evaluate technical provenance, fail-closed behavior, privacy, determinism, output invariance, and gold correctness on public-safe templates that were not used for scope selection, policy design, verifier design, model training, or dev/test debugging.

## Goals / Non-Goals

**Goals:**

- Reject misleading non-default shadow config values that are currently reserved/no-op.
- Load and validate the frozen policy once per prediction run, reuse that immutable snapshot, and detect policy drift after the run.
- Add a sidecar path conflict guard so shadow output cannot overwrite prediction JSONL, prediction metadata, raw generation summaries, prompt snapshots, or generation traces.
- Build and freeze `copy-shadow-template-disjoint-challenge-v1` with public-safe rows, condition tags, template-disjoint audit, challenge hash, and gold verification feasibility.
- Evaluate the challenge through the canonical `voice2task-train sft-predict` / `run_sft_prediction_export` hook path when a verifiable frozen adapter is available.
- Separate gold-free online sidecars from offline evaluation audits.
- Publish compact public-safe evidence, Wilson intervals, latency, policy freeze, privacy, and bounded decision artifacts.

**Non-Goals:**

- No SFT, DPO, GRPO, model retraining, adapter modification, base-model change, prompt change, decoding change, policy change, enabled-triple change, evaluator change, layered-evaluator change, prediction repair, gold repair, schema migration, runtime enforcement, action enablement, normalized trusted provenance, URL resolver, ambiguity representation, challenge-v2 creation, or merge of challenge rows into train/dev/test.
- No claim of slot accuracy improvement, broad model generalization, executable quality improvement, production readiness, safety readiness, live-browser performance improvement, checkpoint release, or adapter release.

## Decisions

1. **Challenge rows are new public sample artifacts, not training data.**
   - Store frozen rows at `data/public-samples/copy-shadow-template-disjoint-challenge-v1.jsonl`.
   - Store report artifacts at `reports/public-sample/copy-shadow-template-disjoint-challenge-v1/`.
   - Alternative considered: keep challenge rows only under reports. Rejected because the manifest must be independently addressable and hashable before prediction.

2. **Template disjointness is deterministic.**
   - Use sample id, exact input text, canonical template signature, slot-value-stripped signature, character 3-gram Jaccard, normalized edit similarity, and known family labels.
   - Filter near-duplicates before freezing. Do not use an LLM judge.
   - Alternative considered: manual-only review. Rejected because near-duplicate thresholds must be reproducible.

3. **Frozen policy is loaded once per run.**
   - Convert prediction shadow config into a run-level policy snapshot before iterating prediction rows.
   - Reuse that policy object/hash for every hook invocation.
   - Check the policy file hash again after the run and report `policy_drift_detected`.
   - Alternative considered: load policy per row. Rejected because challenge evidence must prove run-level freeze.

4. **Reserved config fields fail closed when set non-default.**
   - `retain_input_text=true`, `retain_raw_model_output=true`, and `fail_isolated=false` are explicit configuration errors for this phase.
   - The primary prediction path remains fail-isolated; the hook records a bounded configuration status rather than mutating output.
   - Alternative considered: silently ignore values. Rejected because the previous review found that misleading config surface weakens privacy evidence.

5. **Adapter availability controls observed vs blocked outcome.**
   - If verifiable frozen Control/Treatment adapters and their identity metadata are available, run both on the frozen challenge.
   - If only one frozen current adapter is verifiable, run it and lower the evidence classification to single-model evidence.
   - If no verifiable adapter is available, write `blocked.json` with `CHALLENGE_EVALUATION_BLOCKED` and stop after challenge freeze/hardening validation.
   - Alternative considered: use fixture predictions as the main result. Rejected because the requested phase requires canonical prediction-hook evaluation over frozen adapter prediction-only inference. Fixture paths may remain for tests and fail-isolation probes only.

6. **Online sidecars stay gold-free; correctness is offline.**
   - Online sidecars contain only hashes, policy metadata, hook status, write status, and slot diagnostics.
   - Offline audits join sidecars to frozen gold after prediction/sidecar artifacts are frozen.
   - Alternative considered: add gold correctness directly to sidecars. Rejected because it would violate the current interface split.

7. **Decision labels are conservative.**
   - `FROZEN_POLICY_CHALLENGE_VALIDATED_OBSERVE_ONLY` requires all technical gates plus overall trusted gold-correct rate >= 0.80 and every enabled scope >= 0.70.
   - Scope limitations or blocked adapter availability must produce the corresponding non-enforcement label.
   - No result in this change can recommend runtime enforcement.

## Risks / Trade-offs

- [Risk] Verifiable frozen adapters are unavailable locally or on the A100 machine. -> Mitigation: write blocked evidence after challenge freeze and hardening validation; do not train or fabricate predictions.
- [Risk] Challenge rows accidentally reuse prior templates. -> Mitigation: deterministic disjoint audit with strict filtering before freeze.
- [Risk] Public challenge rows leak private-looking details. -> Mitigation: synthetic-only PII labels, leak scan, default hash/offset sidecars, and committed privacy audit counts.
- [Risk] Trusted provenance is misread as task correctness. -> Mitigation: separate `trusted_but_gold_mismatch` metrics and docs; final labels remain observe-only.
- [Risk] Sidecar path conflicts could corrupt primary artifacts. -> Mitigation: canonical path comparison and isolated conflict status.

## Migration Plan

1. Add hook hardening and tests.
2. Materialize candidate challenge rows and deterministic audits.
3. Freeze challenge v1 and its manifest hash before any prediction.
4. Run canonical prediction hook evaluation only if frozen adapter identity is verifiable.
5. Generate reports/docs/Human Brief.
6. Run full verification and reviewer pass.
7. Archive the OpenSpec change and stop.

Rollback is straightforward: the hook remains default-off; challenge artifacts and report scripts can be reverted without changing model/runtime/evaluator behavior.

## Open Questions

- Which frozen adapter artifacts are available and identity-verifiable in the current local/A100 environment?
- If both Control and Treatment adapters are unavailable, should the blocked report include only challenge/hardening evidence or also fixture-only hook probes? Default: blocked report plus fixture-only tests, with no challenge policy validation label.
