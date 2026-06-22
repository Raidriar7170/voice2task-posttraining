# Voice2Task Current Context

## 1. Project Scope

Voice2Task Post-Training is an evidence-first companion project for Chinese spoken command / ASR transcript -> schema-valid browser task contracts. The project studies public-safe SFT/DPO data construction, Qwen2.5-7B-Instruct + LoRA training paths, prediction artifacts, strict contract evaluation, and offline schema projections. It is not a browser controller, GUI action policy learner, generic chat fine-tune, checkpoint release, or production system.

## 2. Current Formal Data Boundary

The current formal public sample is `public-sample-20260619T090925Z` in `data/public-samples/manifest_public_sample.json`: 247 seeds / 696 SFT rows / 2100 DPO pairs, with train/dev/test = 282/207/207. This boundary was produced by the canonical slot-boundary formal merge and is the current data boundary only; it is not a model-quality claim.

Prior manifests, prior prediction runs, and prior A100 training retries are historical unless explicitly marked `CURRENT` in `reports/public-sample/EVIDENCE_INDEX.md`.

## 3. Latest Model Experiment

The latest model experiment is the one-seed step-matched canonical-slot SFT ablation under `reports/public-sample/step-matched-canonical-slot-ablation/`. Control and Treatment used the same explicit 3132 optimizer-step budget, frozen dev/test inputs, same evaluator, same decoding boundary, and private unreleased Qwen2.5-7B-Instruct LoRA adapters.

The canonical slot treatment under the step-matched condition has no stable general benefit. The result is mixed / statistically inconclusive: some strict exact numbers improve, but guardrails do not establish broad canonical-data gain. It does not trigger a 3-seed confirmation, DPO/GRPO, another small canonical-candidate loop, adapter/checkpoint release, production readiness, safety readiness, held-out recovery, or live-browser claim.

## 4. Latest Architecture Experiment

The latest architecture experiment is the recovered-input Contract V2 offline projection under `reports/public-sample/contract-v2-projection/rerun-with-recovered-inputs/summary.json`. It used recovered metric-reproduced step-matched prediction contracts and aligned gold contracts from `reports/public-sample/step-matched-canonical-slot-ablation/raw-inputs/`.

Decision: `PARTIAL_SCHEMA_BENEFIT`. Derived-field-only strict failures are 14.65%; normalized-command-only strict failures are 14.65%; metadata-only failures are 0%. V2 core exact improves slightly by +0.0193 / +0.0386 for Control dev/test and +0.0290 / +0.0242 for Treatment dev/test. V2 executable pass has no improvement. Renderer support is 99.88%; deterministic roundtrip is 1.0. Core slot failures remain the dominant bottleneck at about 68.79%.

No model weights changed during the Contract V2 projection. No training, prediction rerun, prediction repair, evaluator relaxation, schema implementation, LLM judge, semantic-equivalence scoring, checkpoint release, or adapter release occurred.

## 5. Current Technical Interpretation

strict exact remains canonical diagnostic. The Contract V2 projection only reduces derived/display-field burden, mainly `normalized_command`; it does not repair core slot errors and does not improve executable contract pass. The main engineering bottleneck is still slot representation / slot error mechanisms, not whether another small canonical candidate loop should be run.

Projection follow-up `decide-contract-v2-core-implementation-scope` is now closed by an internal boundary implementation. The internal Contract V2 Core status is `INTERNAL_V2_CORE_READY_RENDERER_PARTIAL`: 2185 current public-safe V1 contracts passed preserve_legacy roundtrip with exact V1 compatibility, safety preservation, confirmation preservation, and slot preservation all at 1.0; V1 evaluator metric deltas are all 0. The derive_display renderer remains partial at 99.77% support with 5 unsupported cases, so it is not the default path.

Contract V2 should not be packaged as model improvement. The external schema remains BrowserTaskContract V1, the training target remains V1, downstream runtime remains V1, and the internal Core boundary exists only as a shadow-compatible engineering boundary.

The internal-core recommendation `analyze-slot-error-mechanisms-and-design-slot-representation` is now completed as read-only analysis/design evidence under `reports/public-sample/slot-error-mechanism-analysis/summary.json`. Decision: `MIXED_SLOT_REPRESENTATION_REQUIRED`. Gold exact/normalized source-copyable slots are 50.53%; typed-derivable slots are 0.00%; source-absent or generation-required slots are 49.47%; prediction unsupported-by-source is 32.17%. Control/Treatment paired movement is persistent=70, recovered=10, regressed=12, net=-2. This does not change BrowserTaskContract V1, ContractCoreV2, evaluators, training targets, predictions, data, or downstream runtime.

The follow-up `design-hybrid-slot-representation-v1` is now completed as design-only evidence under `reports/public-sample/hybrid-slot-representation-v1/summary.json`. Decision: `HYBRID_DESIGN_READY_COPY_SLICE_FIRST`. HybridSlotValue is proposed with model-authored `value` and system-derived `value_type`, `representation_kind`, `source_span`, `normalization_rule`, `verification_status`, `provenance`, and `fallback_behavior`. Source spans use Unicode character offsets with start inclusive and end exclusive. Feasibility coverage is 100.00%; copy-backed coverage is 57.32%; bounded structured coverage is 31.21%; unresolved coverage is 11.46%; current predictions are deterministically verifiable at 51.80% and fail-closed at 48.20%. This does not implement the hybrid representation, migrate V1 schema, change ContractCoreV2, change evaluators, rerun predictions, train, or claim model/executable improvement.

The follow-up `implement-copy-backed-slot-verification-slice` is now completed as offline sidecar-only evidence under `reports/public-sample/copy-backed-slot-verification-slice/summary.json`. Decision: `COPY_SLICE_READY_FOR_SHADOW_INTEGRATION`. Enabled task-scoped triples are `extract:extract_page:target`, `form_fill:fill_form:field`, and `search:search_web:query`; `action` remains disabled and analysis-only. Gold unique verified span rate is 86.38%; Control/Treatment source-verified prediction rate over eligible events is 87.44%; source-verified-and-gold-correct rate is 92.29%; source-verified-but-gold-mismatch rate is 7.71%. Provenance false accepts, silent fallbacks, and V1 evaluator metric deltas are all 0. This does not change predictions, gold contracts, BrowserTaskContract V1, ContractCoreV2, evaluators, training targets, model weights, prompts, runtime behavior, or action semantics.

## 6. Current Claim Boundaries

Current evidence cannot claim model improvement. It cannot claim executable quality improvement. It cannot claim production readiness. It cannot claim safety readiness. It cannot claim held-out recovery. It cannot claim live-browser benchmark gain. It cannot claim checkpoint release. It cannot claim adapter release. It cannot claim DPO justification. It cannot claim another canonical-candidate loop.

Do not merge metrics across manifests. Do not treat JSON validity, executable smoke, train-internal success, or derived-field projection as model capability recovery. Do not delete or rewrite negative, blocked, superseded, or historical results.

## 7. Current Recommended Next Change

The single recommended next technical change is `integrate-copy-backed-slot-verification-shadow-mode`. It should be a bounded shadow-mode slice unless explicitly expanded: attach the verifier to eligible `query`, `field`, and `target` predictions as sidecar-only diagnostics, compare with existing reports, and keep BrowserTaskContract V1 as the external schema.

Do not automatically implement runtime enforcement, action enablement, the full hybrid system, training, data expansion, a challenge set, schema changes, ContractCoreV2 changes, evaluator changes, prediction repair, or model/executable improvement claims.

## 8. Evidence Index Link

Use `reports/public-sample/EVIDENCE_INDEX.md` for the unified evidence map and `reports/public-sample/evidence-index.json` for the machine-readable classification. Raw report directories under `reports/public-sample/<phase>/` remain authoritative and unchanged.
