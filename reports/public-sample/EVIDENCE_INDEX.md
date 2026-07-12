# Public Sample Evidence Index

This index is the navigation layer for public Voice2Task evidence. Raw report
artifacts remain authoritative; this file only classifies them so current,
historical, superseded, blocked, design-only, raw-input, and archived evidence
are not mixed in README or CONTEXT.

Allowed statuses: `CURRENT`, `HISTORICAL`, `SUPERSEDED`, `BLOCKED`,
`DESIGN_ONLY`, `RAW_INPUT`, `ARCHIVED`.

## Current Evidence

| status | phase | manifest/model boundary | conclusion | superseded by | path |
| --- | --- | --- | --- | --- | --- |
| CURRENT | formal-public-sample-boundary | `public-sample-20260619T090925Z`; 247 seeds / 696 SFT rows / 2100 DPO pairs | Dev/test are `DEVELOPMENT_ONLY_SPENT`, not blind, independent, leakage-free, or final-generalization evidence; historical artifacts and metrics remain preserved. | - | `data/public-samples/manifest_public_sample.json` |
| CURRENT | repair-review-findings-before-contract-compiler-audit (`public-split-integrity-audit`) | deterministic audit over 247 seeds and the frozen 696-row SFT artifact | `DEVELOPMENT_ONLY_SPENT`; 8 cross-split digit templates, 4 held-out exact-input rows overlapping train, and 33 train rows with dev/test provenance; lexical/provenance evidence only. | - | `reports/public-sample/split-integrity-audit/summary.json` |
| CURRENT | audit-contract-compiler-v2-causal-boundary | archived audit-only fixed 247-seed renderer population plus explicit public-safe aggregate evidence; no model run | `ARCHIVED`; compiler/model causal identification `CAUSAL_IDENTIFICATION_BLOCKED`, mechanics `DESCRIPTIVE_ONLY`; 98/247 legacy exact, 148 supported mismatches; 99.77% historical support is not legacy canonical exact compatibility; candidate graph is `NOT_IMPLEMENTED_HYPOTHETICAL` and `runtime_wired=false`. | - | `reports/public-sample/contract-compiler-v2-causal-boundary/summary.json` |
| CURRENT | run-lockbox-v1-final-evaluation (`lockbox-v1-final-evaluation`) | frozen 120-row / 120-family lockbox-v1; one-look `unified_gold_free_v1`; aggregate-only | Final SFT strict exact 0.0083 versus base 0.0167 (delta -0.0083): no strict-exact improvement under the frozen protocol; no row-level failure, natural-ASR generalization, overall SFT causal-effect, or general model-quality claim. | - | `reports/lockbox-v1/final-evaluation/comparison.json` |
| CURRENT | implement-internal-contract-v2-core-and-v1-compatible-envelope | internal V2 Core boundary over current committed public-safe V1 contracts | `INTERNAL_V2_CORE_READY_RENDERER_PARTIAL`; preserve_legacy V1 roundtrip exact 1.0; V1 metrics zero delta; derive_display 99.77% support with 5 unsupported cases. | - | `reports/public-sample/internal-contract-v2-core/summary.json` |
| CURRENT | analyze-slot-error-mechanisms-and-design-slot-representation | recovered step-matched slot-level residual analysis | `MIXED_SLOT_REPRESENTATION_REQUIRED`; exact/normalized source-copyable 50.53%; typed-derivable 0.00%; generation-required 49.47%; led to hybrid representation design. | - | `reports/public-sample/slot-error-mechanism-analysis/summary.json` |
| CURRENT | design-hybrid-slot-representation-v1 | design-only hybrid slot representation over current slot analysis artifacts | `HYBRID_DESIGN_READY_COPY_SLICE_FIRST`; copy-backed coverage 57.32%; bounded structured coverage 31.21%; unresolved 11.46%; next change `implement-copy-backed-slot-verification-slice`. | - | `reports/public-sample/hybrid-slot-representation-v1/summary.json` |
| CURRENT | implement-copy-backed-slot-verification-slice | offline sidecar-only verifier over recovered step-matched contracts | `COPY_SLICE_READY_FOR_SHADOW_INTEGRATION`; enabled task-scoped `query`/`field`/`target`; gold unique verified span rate 86.38%; source-verified prediction rate 87.44%; false accepts and silent fallbacks 0. | - | `reports/public-sample/copy-backed-slot-verification-slice/summary.json` |
| CURRENT | integrate-copy-backed-slot-verification-shadow-mode | offline shadow sidecars over recovered step-matched prediction contracts | `SHADOW_MODE_READY_FOR_REVIEW`; 828/828 prediction contracts have sidecars; enforcement enabled 0; action source-verified 0; V1 evaluator metric delta 0. | - | `reports/public-sample/copy-backed-verification-shadow-mode/summary.json` |
| CURRENT | review-copy-backed-shadow-mode-before-runtime-wiring | review-and-hardening split of online sidecars from offline audits | `SHADOW_INTERFACE_READY_FOR_PREDICTION_HOOK`; 828/828 gold-free online sidecars; 942 offline audit rows; trusted exact rate 87.44%; false accepts/silent fallbacks/contract mutations/runtime deltas/action trusted/normalized trusted all 0. | - | `reports/public-sample/copy-backed-shadow-mode-review/summary.json` |
| CURRENT | integrate-copy-backed-verification-prediction-shadow-hook | default-off prediction-pipeline sidecar hook over public fixture predictions | `PREDICTION_SHADOW_HOOK_READY_OBSERVE_ONLY`; disabled/NullSink/JsonlSink prediction output hashes match; deterministic rerun true; V1 metric delta 0; no enforcement. | - | `reports/public-sample/copy-backed-prediction-shadow-hook/summary.json` |
| CURRENT | recover-and-run-frozen-adapter-challenge-evaluation | frozen public-safe template-disjoint challenge v1 over recovered step-matched adapters | `CHALLENGE_V1_HOOK_UNSAFE_OR_INVALID`; 6 Control/Treatment prediction runs; output and parsed-contract invariance across hook modes; 252 offline audit rows; source-absent false trust 3, normalization-collision false trust 6, partial-span false trust 3; no enforcement. | - | `reports/public-sample/copy-shadow-template-disjoint-challenge-v1/adapter-evaluation/challenge-evaluation-summary.json` |
| CURRENT | diagnose-copy-shadow-false-trust-before-naturalistic-v2 | offline false-trust diagnosis over committed challenge v1 artifacts | `SOURCE_ATTESTATION_HARDENED_SCOPE_REDUCTION_REQUIRED`; 16 source-attested-but-gold-mismatch cases; 6 normalized-equivalent collision downgrades; execution eligible 0; next change `design-copy-shadow-scope-policy-v2`. | - | `reports/public-sample/copy-shadow-false-trust-diagnosis/summary.json` |
| CURRENT | rerun-contract-v2-projection-with-recovered-inputs | recovered step-matched contracts from `step-matched-canonical-slot-ablation-20260620T000000Z` | `PARTIAL_SCHEMA_BENEFIT`; derived-field-only strict failures 14.65%; metadata-only 0%; V2 core exact improves slightly; V2 executable pass does not improve. | - | `reports/public-sample/contract-v2-projection/rerun-with-recovered-inputs/summary.json` |
| CURRENT | run-step-matched-canonical-slot-ablation | one-seed step-matched SFT-only comparison; 3132 optimizer steps per arm | Mixed / statistically inconclusive; no stable general canonical-slot data benefit. | - | `reports/public-sample/step-matched-canonical-slot-ablation/comparison.json` |
| CURRENT | merge-canonical-slot-boundary-row-level-candidates | produced `public-sample-20260619T090925Z` | Current data-boundary evidence only; no training, prediction, or model-quality claim. | - | `reports/public-sample/canonical-slot-boundary-formal-merge/manifest.json` |

## Historical Training Runs

| status | phase | manifest/model boundary | conclusion | superseded by | path |
| --- | --- | --- | --- | --- | --- |
| HISTORICAL | retry-scaled-public-sample-current-123-adapter-prediction-baseline-after-a100-recovery | `public-sample-20260617T152259Z`; `a100-current-123-train-split-sft-retry` | Prior-manifest prediction-only evidence; not directly comparable to the current formal data boundary. | - | `reports/public-sample/a100-scaled-public-sample-current-123-adapter-prediction-baseline-after-a100-recovery/manifest.json` |
| HISTORICAL | run-formal-heldout-prediction | older formal public sample; `a100-form-fill-remediation-sft-v3` | Earlier held-out prediction evidence; not the current snapshot. | - | `reports/public-sample/a100-formal-public-heldout-prediction/report.md` |
| HISTORICAL | run-a100-current-123-train-split-sft-retry | `public-sample-20260617T045941Z`; `a100-current-123-train-split-sft-retry` | Historical model evidence before the current canonical slot-boundary formal data boundary. | - | `reports/public-sample/a100-current-123-train-split-sft-retry/manifest.json` |
| HISTORICAL | retry-a100-form-fill-remediation-sft-v3-after-ssh-recovery | `public-sample-20260616T074315Z`; `a100-form-fill-remediation-sft-v3` | Historical setup/model evidence from an older manifest boundary. | - | `reports/public-sample/a100-form-fill-remediation-sft-v3-retry-after-ssh-recovery/manifest.json` |

## Superseded Evidence

| status | phase | manifest/model boundary | conclusion | superseded by | path |
| --- | --- | --- | --- | --- | --- |
| SUPERSEDED | run-canonical-slot-paired-sft-ablation | earlier paired SFT comparison before optimizer-step matching | Useful background, but no longer the current canonical-slot causal result. | `step-matched-canonical-slot-ablation` | `reports/public-sample/canonical-slot-paired-sft-ablation/comparison.json` |
| SUPERSEDED | propose-canonical-slot-boundary-formal-merge-after-review | proposal/readiness evidence before row-level source existed | Superseded by row-level materialization and formal merge evidence. | `canonical-slot-boundary-formal-merge` | `reports/public-sample/canonical-slot-boundary-formal-merge-proposal/summary.json` |
| SUPERSEDED | materialize-canonical-slot-boundary-row-level-candidates | standalone candidate rows before formal promotion | Superseded by the canonical slot-boundary formal merge. | `canonical-slot-boundary-formal-merge` | `reports/public-sample/canonical-slot-boundary-row-level-candidates/manifest.json` |
| SUPERSEDED | must-fix-phase-3-lockbox-lineage-guard | historical validator and one-look setup before real frozen rows existed | Historical blocked setup preserved; superseded after lockbox-v1 was authored, frozen, and evaluated once. | `lockbox-v1-final-evaluation` | `docs/lockbox.md` |

## Blocked Runs

| status | phase | manifest/model boundary | conclusion | superseded by | path |
| --- | --- | --- | --- | --- | --- |
| BLOCKED | materialize-and-freeze-clean-compiler-model-evaluation-boundary-v1 | archived S0 source/binding gate; no independent clean acquisition frame; 0/29 reviewed bindings | `CLEAN_EVALUATION_BOUNDARY_MATERIALIZATION_BLOCKED`; state `DESIGN_ONLY`, protocol `NOT_FROZEN`, population `NOT_MATERIALIZED`, integrity `NOT_CREATED`; both partitions not materialized and one-look unavailable; no private artifacts, clean rows, training, prediction, A100, experiment, or claim. | - | `reports/public-sample/clean-compiler-model-evaluation-boundary-v1/summary.json` |
| BLOCKED | design-and-evaluate-contract-v2-projection | initial Contract V2 projection before raw contracts were recovered | `PROJECTION_BLOCKED_OR_INVALID`; current raw prediction/gold contracts were missing. | `contract-v2-projection-rerun` | `reports/public-sample/contract-v2-projection/summary.json` |
| BLOCKED | evaluate-frozen-copy-shadow-policy-on-template-disjoint-challenge-set | freeze-phase template-disjoint challenge v1 before adapter recovery | `CHALLENGE_EVALUATION_BLOCKED_ADAPTER_UNAVAILABLE`; challenge/policy freeze and hook hardening evidence only; superseded by recovered adapter evaluation. | `recover-and-run-frozen-adapter-challenge-evaluation` | `reports/public-sample/copy-shadow-template-disjoint-challenge-v1/blocked.json` |
| BLOCKED | run-current-canonical-boundary-prediction-baseline | `public-sample-20260619T090925Z`; current-boundary prediction attempt | Blocked before A100 prediction; no current model metrics. | - | `reports/public-sample/a100-current-canonical-boundary-prediction-baseline/manifest.json` |
| BLOCKED | run-scaled-public-sample-current-123-adapter-prediction-baseline | `public-sample-20260617T152259Z`; prior scaled-manifest prediction attempt | Historical blocked prediction baseline with no current model metrics; later recovered by a separate retry. | `a100-scaled-current-123-baseline-after-recovery` | `reports/public-sample/a100-scaled-public-sample-current-123-adapter-prediction-baseline/manifest.json` |

## Design-Only Evidence

| status | phase | manifest/model boundary | conclusion | superseded by | path |
| --- | --- | --- | --- | --- | --- |
| DESIGN_ONLY | prepare-clean-evaluation-acquisition-and-binding-review-pack-v1 | `PREPARATION_ONLY` non-executable operator guidance; canonical 29-item inventory; supplied bindings 0/29; authoritatively bound 0; independent acquisition source `UNAVAILABLE` | `ACQUISITION_AND_BINDING_REVIEW_PACK_READY_EXECUTION_BLOCKED`; review pack `READY_FOR_EXTERNAL_COMPLETION` only, candidate pack `INCOMPLETE`; protocol `NOT_FROZEN`, population `NOT_MATERIALIZED`, human acceptance `NOT_RECORDED`, `freeze_authorized=false`, `next_phase_eligible=false`, `execution_readiness=false`; not a source, reviewed binding packet, frozen protocol, clean population, or executable experiment; archived S0 remains blocked and unsuperseded. | - | `reports/public-sample/clean-evaluation-acquisition-and-binding-review-pack-v1/summary.json` |
| DESIGN_ONLY | preregister-clean-matched-compiler-and-model-evidence-design | exactly 10 public-safe aggregate sources; one future acquisition; two future family-disjoint one-look partitions; 29/29 execution bindings `UNBOUND_BY_DESIGN` | `PREREGISTRATION_DESIGN_READY_EXECUTION_BLOCKED`; protocol `NOT_FROZEN`, population `NOT_MATERIALIZED`, experiment `NOT_EXECUTABLE`, `execution_readiness=false`; both causal estimands blocked; follow-up materialization is separately recorded as S0 blocked. | - | `reports/public-sample/clean-matched-causal-evidence-design/summary.json` |
| DESIGN_ONLY | design-slot-canonicalization-policy | no formal data or model mutation | Policy analysis only; no data, training, evaluator, or model improvement claim. | - | `reports/public-sample/slot-canonicalization-policy/summary.json` |
| DESIGN_ONLY | design-safety-repair-candidates | no formal data or model mutation | Candidate design only; no materialization, training, or evaluator change. | - | `reports/public-sample/safety-repair-candidate-design/manifest.json` |
| DESIGN_ONLY | design-scaled-clarify-slot-boundary-candidates | no formal data or model mutation | Candidate design only; not current model evidence and not the current recommended next change. | - | `reports/public-sample/scaled-clarify-slot-boundary-candidate-design/manifest.json` |
| DESIGN_ONLY | design-scaled-public-sample-and-tiered-eval | no formal data or model mutation | Strategic planning evidence only. | - | `reports/public-sample/scaled-public-sample-and-tiered-eval-design/manifest.json` |

## Raw/Reproducibility Inputs

| status | phase | manifest/model boundary | conclusion | superseded by | path |
| --- | --- | --- | --- | --- | --- |
| RAW_INPUT | recover-step-matched-projection-inputs | recovered public-safe contracts; 207 dev rows and 207 test rows | `RECOVERED_FROM_EXISTING_ARTIFACTS`; boundary and metric reproduction passed. | - | `reports/public-sample/step-matched-canonical-slot-ablation/raw-inputs/artifact-manifest.json` |

## Archived Process Evidence

| status | phase | manifest/model boundary | conclusion | superseded by | path |
| --- | --- | --- | --- | --- | --- |
| ARCHIVED | openspec-change-history | archived OpenSpec proposal/design/task history | Process evidence only; not runtime model evidence by itself. | - | `openspec/changes/archive` |

Machine-readable source: [`evidence-index.json`](evidence-index.json).
