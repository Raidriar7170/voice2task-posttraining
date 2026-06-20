# Voice2Task 最终状态说明

更新日期：2026-06-20

## 一句话结论

当前项目可以收束为一个证据完整、边界清楚的 Voice2Task post-training / evaluation baseline：canonical slot-boundary 数据在 one-seed paired SFT A/B 中带来正向 partial signal，但 pilot gate 未通过，不能宣称 held-out recovery、3-seed confirmation readiness、DPO 值得继续、生产可用、checkpoint/adapter 发布或 live-browser benchmark 提升。

## 当前权威证据

| 项目 | 值 |
| --- | --- |
| Latest paired SFT ablation evidence pack | `reports/public-sample/canonical-slot-paired-sft-ablation/` |
| Latest paired SFT comparison | `reports/public-sample/canonical-slot-paired-sft-ablation/comparison.md` |
| Latest paired SFT boundary verification | `reports/public-sample/canonical-slot-paired-sft-ablation/boundary-verification.json` |
| Latest current-canonical-boundary prediction baseline evidence pack | `reports/public-sample/a100-current-canonical-boundary-prediction-baseline/` |
| Latest data evidence pack | `reports/public-sample/canonical-slot-boundary-formal-merge/` |
| Latest scaled-manifest prediction baseline evidence pack | `reports/public-sample/a100-scaled-public-sample-current-123-adapter-prediction-baseline-after-a100-recovery/` |
| Latest canonical slot-boundary formal merge evidence pack | `reports/public-sample/canonical-slot-boundary-formal-merge/` |
| Latest canonical slot-boundary row-level candidate materialization evidence pack | `reports/public-sample/canonical-slot-boundary-row-level-candidates/` |
| Latest canonical slot-boundary formal-merge proposal evidence pack | `reports/public-sample/canonical-slot-boundary-formal-merge-proposal/` |
| Latest canonical slot-boundary candidate review evidence pack | `reports/public-sample/canonical-slot-boundary-candidate-review/` |
| Latest canonical slot-boundary candidate materialization evidence pack | `reports/public-sample/canonical-slot-boundary-candidates/` |
| Latest slot canonicalization policy evidence pack | `reports/public-sample/slot-canonicalization-policy/` |
| Latest safety repair candidate-design review evidence pack | `reports/public-sample/safety-repair-candidate-design-review/` |
| Latest safety repair candidate-design evidence pack | `reports/public-sample/safety-repair-candidate-design/` |
| Latest residual-driven remediation target selection evidence pack | `reports/public-sample/remediation-target-selection/` |
| Latest layered evaluation evidence pack | `reports/public-sample/layered-eval/` |
| Latest residual diagnosis evidence pack | `reports/public-sample/residual-diagnosis/` |
| Latest scaled clarify slot-boundary candidate materialization evidence pack | `reports/public-sample/scaled-clarify-slot-boundary-candidate-materialization/` |
| Latest scaled remediation target selection evidence pack | `reports/public-sample/scaled-residual-remediation-target-selection/` |
| Latest scaled clarify slot-boundary candidate-design evidence pack | `reports/public-sample/scaled-clarify-slot-boundary-candidate-design/` |
| Latest scaled-manifest residual cluster inspection evidence pack | `reports/public-sample/scaled-current-123-adapter-residual-cluster-inspection/` |
| Latest scaled-manifest residual diagnosis evidence pack | `reports/public-sample/scaled-current-123-adapter-residual-diagnosis/` |
| Prior blocked scaled-manifest baseline evidence pack | `reports/public-sample/a100-scaled-public-sample-current-123-adapter-prediction-baseline/` |
| Latest standalone scaled candidate evidence pack | `reports/public-sample/scaled-public-sample-candidate-materialization/` |
| Latest readiness evidence pack | `reports/public-sample/current-123-train-split-sft-retry-readiness/` |
| Latest model evidence pack | `reports/public-sample/canonical-slot-paired-sft-ablation/` |
| Latest observed model evidence pack | `reports/public-sample/canonical-slot-paired-sft-ablation/` |
| Prior current-123 model evidence pack | `reports/public-sample/a100-current-123-train-split-sft-retry/` |
| Latest strategic-design evidence pack | `reports/public-sample/scaled-public-sample-and-tiered-eval-design/` |
| Latest candidate-design evidence pack | `reports/public-sample/current-retry-confirmation-preservation-candidate-design/` |
| Latest prior-manifest diagnosis evidence pack | `reports/public-sample/current-train-split-sft-retry-tradeoff-diagnosis/` |
| Baseline evidence pack | `reports/public-sample/a100-formal-public-heldout-prediction-after-a100-recovery/` |
| Current data manifest | `public-sample-20260619T090925Z` |
| Current public sample | 247 seeds / 696 SFT rows / 2100 DPO pairs |
| Current split | train 282 / dev 207 / test 207 |
| Latest evaluated manifest | frozen dev/test from `public-sample-20260619T090925Z`, verified identical to `public-sample-20260617T152259Z` dev/test |
| Latest evaluated public sample | control boundary 240 seeds / 675 SFT rows / 2046 DPO pairs; treatment boundary 247 seeds / 696 SFT rows / 2100 DPO pairs |
| Latest run type | one-seed paired SFT A/B with fresh control and treatment adapters; no old adapter as control; no DPO/GRPO |
| Latest interpretation | `canonical_slot_paired_sft_ablation_gate_failed` |
| Latest observed interpretation | positive partial signal, but gate failed because test `slot_value_exact_f1` delta is `+0.027740`, below the required `+0.03`; recommended next step is `design-and-implement-contract-v2` |
| Latest canonical slot paired SFT result | boundary verified identical dev/test gold; control trained on 261 SFT rows, treatment trained on 282 SFT rows; dev/test executable deltas are `+0.053140` / `+0.028986`; dev/test slot exact deltas are `+0.051282` / `+0.027740`; safety recall did not drop |
| Latest canonical slot paired SFT recommended next step | do not add more candidate-only rows or run DPO; move next to `design-and-implement-contract-v2` if continuing |
| Latest canonical slot-boundary formal merge result | exactly 7 reviewed train-only canonical slot-boundary candidate seeds promoted into formal public sample; formal SFT/DPO/manifest rebuilt; comparison boundary changed; no training/prediction/A100/prompt/postprocessor/evaluator/model-quality claim in that earlier phase |
| Latest canonical slot-boundary formal merge recommended next step | completed by the later paired SFT ablation; old unpaired metrics remain not directly comparable |
| Latest canonical slot-boundary row-level candidate materialization result | 7 train-only standalone candidate seed rows in `data/public-samples/canonical_slot_boundary_seed_candidates.jsonl`; 21 report-local SFT preview rows; no formal data mutation |
| Latest canonical slot-boundary row-level candidate materialization recommended next step | completed by the later bounded formal merge phase; keep this as phase-sequence evidence |
| Latest canonical slot-boundary formal-merge proposal result | prior proposal/readiness only; `formal_merge_ready_now=false`, `formal_merge_readiness=not_ready_missing_row_level_candidate_source`, `implemented_now=false` in that phase |
| Latest canonical slot-boundary formal-merge proposal recommended next step | completed by the row-level materialization phase; do not treat the old proposal as direct merge approval |
| Latest strategic-design interpretation | `scale_data_and_diagnose_by_tier_before_another_training_retry` |
| Latest scaled-manifest cluster interpretation | `scaled_current_123_residual_clusters_clarify_slots_top_cluster` |
| Latest canonical slot-boundary candidate review result | review-only class decisions: slot-key aliases and conservative slot-value boundaries are eligible only for later bounded formal-merge proposal; normalized-command examples are diagnostic/display-only; excluded non-equivalence cases remain blocked/deferred |
| Latest canonical slot-boundary candidate review recommended next step | `propose-canonical-slot-boundary-formal-merge-after-review`, separate bounded OpenSpec proposal only |
| Latest canonical slot-boundary candidate result | standalone report-local public-safe examples only; no formal data/SFT/DPO/manifest/prediction/training/evaluator change |
| Latest slot canonicalization policy result | design-only policy: slot keys comparatively stable; slot values and `normalized_command` dominate strict residuals |
| Latest slot canonicalization recommended next step | use review evidence only as input to a later bounded formal-merge proposal; postprocessor/training require separate bounded phases |
| Latest residual-driven remediation target selection | `safety-repair-unsafe-false-negative` first, `slot-value-canonicalization-policy` second |
| Latest safety repair candidate-design review result | 1 row-backed theme ready for later bounded proposal, 1 policy-scoped theme, 1 broad theme deferred; review-only and not materialization approval |
| Latest safety repair candidate-design review recommended next step | `propose_clarify_confirmation_safety_repair_materialization_after_review` |
| Latest safety repair candidate-design result | 3 public-safe themes anchored by 1 current unsafe false negative; design-only |
| Latest safety repair recommended next step | `review_safety_repair_candidates_before_materialization`, now completed as review-only evidence |
| Latest residual-driven recommended next change | `design-safety-repair-candidates`, now completed as design-only evidence |
| Latest scaled remediation target selection | `clarify/slots` = 78 residual rows / 78 residual fields |
| Latest scaled clarify materialization result | 9 standalone candidate seeds / 27 candidate SFT rows / no DPO pairs; standalone-only |
| Latest scaled clarify candidate-design result | 3 themes / 28 source families / 78 source-family incidence; design source |
| Latest scaled-manifest diagnosis interpretation | `scaled_current_123_residuals_slot_and_normalized_command_dominant` |
| Latest prior-manifest diagnosis interpretation | `current_sft_retry_tradeoff_diagnosis_confirmation_regression_after_safety_recovery` |
| Prior SFT v3 retry evidence | `reports/public-sample/a100-form-fill-remediation-sft-v3-retry-after-ssh-recovery/` |

最新 paired SFT ablation 已记录在 `reports/public-sample/canonical-slot-paired-sft-ablation/`。它先证明 control `public-sample-20260617T152259Z` 和 treatment `public-sample-20260619T090925Z` 的 dev/test gold 文件在 row id 顺序、input text 和 gold contracts 上完全一致，然后训练两个 fresh SFT-only adapters：control 使用 261 条 train SFT rows，treatment 使用 282 条 train SFT rows。两组保持相同 Qwen2.5-7B-Instruct base model、LoRA rank/alpha/dropout、learning rate、epoch/max steps、batch/gradient accumulation、random seed、prompt template、tokenizer、decoding parameters、evaluator 和 frozen dev/test inputs。没有复用旧 adapter 当 control，没有 DPO/GRPO，没有 evaluator change、LLM judge、prediction repair 或 semantic-equivalence scoring。

本轮结果是 positive partial signal，但 pilot gate 未通过。Treatment 相比 Control 的 dev/test `slot_value_exact_f1` delta 为 `+0.051282` / `+0.027740`，dev/test `executable_contract_pass_rate` delta 为 `+0.053140` / `+0.028986`，safety recall 没有下降，unsafe false negative 没有增加，confirmation accuracy 没有超过允许下降。但 test `slot_value_exact_f1` 未达到预设 `+0.03` 门槛，因此不建议 3-seed confirmation，不继续少量 canonical candidate loop，不做 DPO。下一步如果继续，应转为 `design-and-implement-contract-v2`。

此前 current-canonical-boundary prediction baseline 已记录在 `reports/public-sample/a100-current-canonical-boundary-prediction-baseline/`。它绑定 `public-sample-20260619T090925Z`，保留 source adapter runtime `a100-current-train-split-sft-retry` 和 source adapter manifest `public-sample-20260617T045941Z`，但 sanitized read-only A100 SSH preflight 超时，未能安全验证 GPU occupancy 或 private adapter，也没有写入 predictions 或 model-quality metrics。状态是 `run_status=blocked` / `formal_public_heldout_prediction_blocked`；这只是当前边界的 fail-closed execution evidence，不是模型效果证据。

此前 A100 recovery prediction-only retry 绑定 `public-sample-20260617T152259Z`，而当前 formal data boundary 已更新为 `public-sample-20260619T090925Z`。它使用已有的 private `a100-current-train-split-sft-retry` adapter，在 scaled dev/test split 上生成预测并用 strict evaluator 评估。没有训练、没有修 prediction、没有 normalize slot、没有改 prompt、没有放松 evaluator。adapter、checkpoint、raw log、private override 和远端缓存都没有发布。它现在是历史模型证据，不是最新 paired SFT A/B 结论。

注意比较边界：这个 adapter 的训练来源是 `public-sample-20260617T045941Z`，本次评估目标是 `public-sample-20260617T152259Z`，当前数据边界又已变为 `public-sample-20260619T090925Z`。因此这份结果是历史 model evidence，不是当前 canonical slot-boundary merged boundary 的 clean improvement/regression comparison。

此前第一次 scaled-manifest prediction-only baseline 尝试仍作为 historical blocked evidence 保留：

- evidence: `reports/public-sample/a100-scaled-public-sample-current-123-adapter-prediction-baseline/report.md`
- status: blocked before A100 prediction because the configured SSH alias timed out

A100 恢复后已完成 observed retry：

- evidence: `reports/public-sample/a100-scaled-public-sample-current-123-adapter-prediction-baseline-after-a100-recovery/report.md`
- target manifest: `public-sample-20260617T152259Z`
- source adapter runtime: `a100-current-train-split-sft-retry`
- source adapter manifest: `public-sample-20260617T045941Z`
- status: observed, prediction-only, no training

随后已完成 scaled-manifest residual-family diagnosis：

- evidence: `reports/public-sample/scaled-current-123-adapter-residual-diagnosis/formal_heldout_residual_family_diagnosis.md`
- source evidence: `reports/public-sample/a100-scaled-public-sample-current-123-adapter-prediction-baseline-after-a100-recovery/formal_public_heldout_prediction.json`
- status: diagnosis-only；没有 A100 job、训练、prediction rerun、数据改动、prompt/evaluator 改动、slot normalization、prediction repair、adapter/checkpoint 发布或 recovery claim；
- residual rows: 321 total = 156 dev / 165 test；
- dominant residual fields: `slots=304`、`normalized_command=194`；
- smaller residual fields: `task_type=13`、`route=13`、`safety=10`、`confirmation_required=6`；
- tiered interpretation: schema/route/safety/confirmation 较强，strict slot 和 full-contract exact 仍弱；
- recommended next bounded decision: `inspect_scaled_residual_clusters_before_data_or_training`。

随后已完成 scaled-manifest residual-cluster inspection：

- evidence: `reports/public-sample/scaled-current-123-adapter-residual-cluster-inspection/formal_heldout_residual_cluster_inspection.md`
- source diagnosis: `reports/public-sample/scaled-current-123-adapter-residual-diagnosis/formal_heldout_residual_family_diagnosis.json`
- status: analysis-only；没有 A100 job、训练、prediction rerun、数据改动、prompt/evaluator 改动、semantic-equivalence scoring、slot normalization、prediction repair、adapter/checkpoint 发布或 recovery claim；
- cluster count: 29；
- source count consistency: 321 residual rows / 540 residual fields，clustered counts 完全一致；
- top clusters: `clarify/slots=78`、`blocked/slots=51`、`search/slots=51`、`form_fill/slots=50`、`blocked/normalized_command=47`；
- recommended next bounded decision: `select_or_design_remediation_target_from_ranked_clusters_before_data_or_training`。

随后已完成 scaled residual remediation target selection：

- evidence: `reports/public-sample/scaled-residual-remediation-target-selection/scaled_residual_remediation_target_selection.md`
- source cluster inspection: `reports/public-sample/scaled-current-123-adapter-residual-cluster-inspection/formal_heldout_residual_cluster_inspection.json`
- status: target-selection only；没有 A100 job、训练、prediction rerun、数据改动、prompt/evaluator 改动、semantic-equivalence scoring、slot normalization、prediction repair、adapter/checkpoint 发布或 recovery claim；
- selected target: `clarify|clarify|ambiguous_request|confirm:true|slots:ambiguity` / `slots`；
- selected residuals: 78 rows / 78 fields；
- deferred safety target: `blocked/slots` 明确留给 dedicated safety boundary phase；
- recommended next bounded decision: `design-scaled-clarify-slot-boundary-candidates`。

随后已完成 scaled clarify slot-boundary candidate design：

- evidence: `reports/public-sample/scaled-clarify-slot-boundary-candidate-design/scaled_clarify_slot_boundary_candidate_design.md`
- status: design-only；没有 public seed rows、SFT rows、DPO pairs、manifest rebuild、训练、prediction、prompt/evaluator 改动、slot normalization、prediction repair、adapter/checkpoint 发布或 model-quality claim；
- source coverage: 28 source families / 78 source-family incidence；
- candidate themes: `clarify_search_or_extract_ambiguity`、`clarify_navigation_or_form_fill_ambiguity`、`clarify_pronoun_or_context_missing`；
- accepted target sketch: `clarify/clarify`、`safety.reason=ambiguous_request`、`confirmation_required=true`、非空 `slots.ambiguity`；
- rejected drift sketches: 错误转成 `search/search_web`、`navigate/open_url`、`form_fill/fill_form` 或 `blocked/deny`；
- recommended next bounded decision: `materialize-scaled-clarify-slot-boundary-candidates`。

随后已完成 standalone scaled clarify slot-boundary candidate materialization：

- evidence: `reports/public-sample/scaled-clarify-slot-boundary-candidate-materialization/scaled_clarify_slot_boundary_candidate_materialization.md`
- candidate seed file: `data/public-samples/scaled_clarify_slot_boundary_seed_candidates.jsonl`
- 从 3 个 reviewed clarify themes 派生 `9` 条 standalone candidate seeds，每个 theme 各 1 条 train/dev/test；
- 派生 `27` 条 SFT candidate rows；
- 所有 target contract 保持 `clarify/clarify`、`safety.reason=ambiguous_request`、`confirmation_required=true`、非空 `slots.ambiguity`；
- 没有合入 formal public sample、没有重建 formal SFT/DPO/manifest、没有生成 DPO pairs、没有训练、没有 prediction、没有 A100 execution、没有改 prompt/evaluator、没有 slot normalization、没有 prediction repair，也不能宣称模型恢复；
- recommended next bounded decision: `merge-scaled-clarify-slot-boundary-candidates`。

随后已完成 additive layered evaluator and residual diagnosis：

- layered evidence: `reports/public-sample/layered-eval/`
- residual evidence: `reports/public-sample/residual-diagnosis/`
- docs: `docs/evaluation.md`
- source evidence: `reports/public-sample/a100-scaled-public-sample-current-123-adapter-prediction-baseline-after-a100-recovery/`
- status: evaluation-only / diagnosis-only；没有 clarify candidate merge、数据扩展、A100 training、prediction rerun、DPO/GRPO、LoRA 参数调整、evaluator relaxation、slot repair、prediction repair、adapter/checkpoint 发布或 model-quality claim；
- strict boundary: `contract_exact_match_strict` 保持原 strict evaluator 输出，dev/test 仍为 `0.2464` / `0.2029`；
- layered signal: executable-contract pass rate 为 `0.2705` / `0.2512`，schema validity 为 `1.0000` / `1.0000`；
- normalization result: bounded deterministic slot-value normalization 没有额外提升当前 slot-value F1，dev/test normalized F1 与 exact F1 同为 `0.2821` / `0.2390`；
- residual result: dev top residual fields 是 `normalized_command=91`、`slots.ambiguity=45`、`slots.field=28`；test top residual fields 是 `normalized_command=103`、`slots.ambiguity=37`、`slots.reason=32`；
- recommended next bounded decision: use residual-driven target selection before choosing any data, training, policy, or evaluator phase；不要默认继续 `merge-scaled-clarify-slot-boundary-candidates`。

随后已完成 residual-driven remediation target selection：

- evidence: `reports/public-sample/remediation-target-selection/summary.md`
- machine-readable evidence: `reports/public-sample/remediation-target-selection/summary.json`
- top failures: `reports/public-sample/remediation-target-selection/top-failures.md`
- next-change prompt seed: `reports/public-sample/remediation-target-selection/recommended-next-change.md`
- status: target-selection only；没有训练、prediction rerun、数据扩展、candidate merge、split 改动、DPO 扩展、LoRA/base-model 改动、evaluator relaxation、LLM judge、semantic-equivalence scoring、prediction repair、adapter/checkpoint 发布或 model-quality claim；
- top 5 failure families: `slot_value_mismatch=336`、`normalized_command_mismatch=194`、`extra_slot=16`、`missing_slot=13`、`route_mismatch=13`（`task_type_mismatch=13` 同量级）；
- selected targets: `safety-repair-unsafe-false-negative`（1 个 unsafe false negative，优先 safety repair）和 `slot-value-canonicalization-policy`（365 个 slot-related residuals，主导项是 `slot_value_mismatch=336`）；
- recommended next bounded change: `design-safety-repair-candidates`；
- current boundary: 这不是 held-out recovery、production readiness、safety readiness、checkpoint/adapter release 或 live-browser benchmark improvement。

随后已完成 safety repair candidate design：

- evidence: `reports/public-sample/safety-repair-candidate-design/safety_repair_candidate_design.md`
- machine-readable evidence: `reports/public-sample/safety-repair-candidate-design/safety_repair_candidate_design.json`
- manifest: `reports/public-sample/safety-repair-candidate-design/manifest.json`
- source artifacts: residual-driven target selection、layered-eval、residual-diagnosis、current public gold/prediction boundary evidence；
- current unsafe false negative: `family-clarify-test-1-aug-1`，gold 是 `clarify/clarify` 且 `confirmation_required=true`，prediction 变成 `search/search_web` 且 `confirmation_required=false`；
- candidate themes: `clarify_confirmation_preservation`、`confirmation_required_boundary`、`unsafe_action_denial_boundary`；
- status: design-only；没有 seed materialization、formal public sample mutation、split change、训练、prediction rerun、DPO/GRPO、prompt/evaluator 改动、evaluator relaxation、LLM judge、semantic-equivalence scoring、prediction repair、adapter/checkpoint release 或 model-quality/safety-readiness claim；
- recommended next bounded step: `review_safety_repair_candidates_before_materialization`。

随后已完成 safety repair candidate design review：

- evidence: `reports/public-sample/safety-repair-candidate-design-review/safety_repair_candidate_design_review.md`
- machine-readable evidence: `reports/public-sample/safety-repair-candidate-design-review/safety_repair_candidate_design_review.json`
- manifest: `reports/public-sample/safety-repair-candidate-design-review/manifest.json`
- source design: `reports/public-sample/safety-repair-candidate-design/safety_repair_candidate_design.json`
- review result: `clarify_confirmation_preservation` is row-backed and ready only for a later bounded materialization proposal; `confirmation_required_boundary` is policy-scoped; `unsafe_action_denial_boundary` is deferred to a separate safety-policy design；
- status: review-only；所有 theme 都保留 `approved_for_materialization=false`；没有 seed materialization、formal public sample mutation、split change、训练、prediction rerun、DPO/GRPO、prompt/evaluator 改动、evaluator relaxation、LLM judge、semantic-equivalence scoring、prediction repair、adapter/checkpoint release 或 model-quality/safety-readiness claim；
- recommended next bounded step: `propose_clarify_confirmation_safety_repair_materialization_after_review`。

随后已完成 slot canonicalization policy：

- evidence: `reports/public-sample/slot-canonicalization-policy/summary.md`
- machine-readable evidence: `reports/public-sample/slot-canonicalization-policy/summary.json`
- policy files: `slot-key-policy.md`、`slot-value-policy.md`、`normalized-command-policy.md`、`model-target-boundary.md`、`recommended-next-change.md`
- status: design-only；没有 formal public sample mutation、SFT/DPO rows、split change、训练、prediction rerun、A100 job、prompt/evaluator 改动、evaluator relaxation、LLM judge、semantic-equivalence scoring、prediction repair、adapter/checkpoint release 或 model-quality claim；
- key conclusion: slot keys are comparatively stable, while slot values and `normalized_command` dominate current strict residuals；
- recommended next bounded step: `materialize-canonical-slot-boundary-candidates`。

随后已完成 canonical slot-boundary candidate materialization：

- evidence: `reports/public-sample/canonical-slot-boundary-candidates/summary.md`
- machine-readable evidence: `reports/public-sample/canonical-slot-boundary-candidates/summary.json`
- leak scan record: `reports/public-sample/canonical-slot-boundary-candidates/leak_scan_result.json`
- status: standalone report-local candidates only；没有 JSONL seed candidates、formal public sample mutation、SFT/DPO rows、manifest rebuild、split change、prediction rerun、训练、A100 job、model config、evaluator code、postprocessor implementation、strict exact relaxation、LLM judge、semantic-equivalence scoring、prediction repair、adapter/checkpoint release 或 model-quality claim；
- accepted groups: `slot_key_aliases`、`slot_value_boundaries`、`normalized_command_display_diagnostic`；
- excluded cases: date、city/location、product、URL host、price/amount、product/query、location/destination、action/reason 非等价合并；
- next step: completed by the canonical slot-boundary candidate review phase。

随后已完成并归档 canonical slot-boundary candidate review：

- evidence: `reports/public-sample/canonical-slot-boundary-candidate-review/summary.md`
- machine-readable evidence: `reports/public-sample/canonical-slot-boundary-candidate-review/summary.json`
- leak scan record: `reports/public-sample/canonical-slot-boundary-candidate-review/leak_scan_result.json`
- source evidence: `reports/public-sample/canonical-slot-boundary-candidates/summary.json`
- review result: `slot_key_aliases` 和 `slot_value_boundaries` 只可作为后续 bounded formal merge proposal 的输入；`normalized_command_display_diagnostic` 仅保持 diagnostic/display；excluded non-equivalence cases 保持 blocked/deferred；
- status: review-only；所有 class 都保留 `approved_for_formal_merge_now=false` 和 `requires_separate_openspec_change=true`；没有 formal public sample mutation、JSONL seed candidates、SFT/DPO rows、manifest rebuild、split change、prediction rerun、训练、A100 job、postprocessor implementation、strict exact relaxation、LLM judge、semantic-equivalence scoring、prediction repair、adapter/checkpoint release 或 model-quality claim；
- recommended next bounded step: `propose-canonical-slot-boundary-formal-merge-after-review`，但本阶段不实现。

随后已完成 canonical slot-boundary formal-merge proposal/readiness：

- evidence: `reports/public-sample/canonical-slot-boundary-formal-merge-proposal/summary.md`
- machine-readable evidence: `reports/public-sample/canonical-slot-boundary-formal-merge-proposal/summary.json`
- leak scan record: `reports/public-sample/canonical-slot-boundary-formal-merge-proposal/leak_scan_result.json`
- source review: `reports/public-sample/canonical-slot-boundary-candidate-review/summary.json`
- result: `formal_merge_ready_now=false`、`formal_merge_readiness=not_ready_missing_row_level_candidate_source`、`implemented_now=false`；
- eligible future classes: `slot_key_aliases`、`slot_value_boundaries`；
- excluded from future formal merge: `normalized_command_display_diagnostic` 和 excluded non-equivalence cases；
- required future source artifact: `data/public-samples/canonical_slot_boundary_seed_candidates.jsonl`，已由后续 row-level materialization phase 创建；
- status: proposal/readiness only；没有 formal public sample mutation、JSONL seed candidates、SFT/DPO rows、manifest rebuild、split change、prediction rerun、训练、A100 job、postprocessor implementation、strict exact relaxation、LLM judge、semantic-equivalence scoring、prediction repair、adapter/checkpoint release 或 model-quality claim；
- recommended next bounded step: 已由 row-level materialization phase 完成；不要把该 proposal/readiness phase 追认为 direct merge approval。

随后已完成 canonical slot-boundary row-level candidate materialization：

- evidence: `reports/public-sample/canonical-slot-boundary-row-level-candidates/canonical_slot_boundary_row_level_candidate_materialization.md`
- machine-readable evidence: `reports/public-sample/canonical-slot-boundary-row-level-candidates/canonical_slot_boundary_row_level_candidate_materialization.json`
- manifest: `reports/public-sample/canonical-slot-boundary-row-level-candidates/manifest.json`
- leak scan record: `reports/public-sample/canonical-slot-boundary-row-level-candidates/leak_scan_result.json`
- candidate seed file: `data/public-samples/canonical_slot_boundary_seed_candidates.jsonl`
- 物化 exactly 7 条 train-only standalone candidate seed rows：`slot_key_aliases=3`、`slot_value_boundaries=4`；
- 派生 21 条 report-local SFT preview rows，只放在 row-level candidate report 目录；
- 所有 rows 都是 `standalone_not_formal_public_sample`，并追溯到 source materialization、archived review、policy file/section 和 manifest `public-sample-20260617T152259Z`；
- `normalized_command_display_diagnostic` 和 excluded non-equivalence cases 没有进入 row-level source；
- status: standalone source only；没有 formal public sample mutation、formal SFT/DPO generation、formal manifest rebuild、split change、prediction rerun、训练、A100 job、postprocessor implementation、strict exact relaxation、LLM judge、semantic-equivalence scoring、prediction repair、adapter/checkpoint release 或 model-quality claim；
- recommended next bounded step: later formal merge review/apply phase can inspect this source；direct merge is not implemented now。

## Formal Public Held-Out 指标（绑定 `public-sample-20260617T152259Z`）

| 指标 | Dev | Test |
| --- | ---: | ---: |
| rows | 207 | 207 |
| json_valid_rate | 1.0000 | 1.0000 |
| task_type_accuracy | 0.9614 | 0.9758 |
| route_accuracy | 0.9614 | 0.9758 |
| safety_precision | 1.0000 | 0.9706 |
| safety_recall | 1.0000 | 1.0000 |
| confirmation_accuracy | 0.9758 | 0.9952 |
| slot_f1 (strict) | 0.2874 | 0.2593 |
| slot_f1_soft (diagnostic only) | 0.6372 | 0.6108 |
| contract_exact_match | 0.2464 | 0.2029 |

主指标是 `contract_exact_match` 和 strict `slot_f1`。`slot_f1_soft` 只能说明 slot value 存在表述相近但 exact 不一致的现象，不能替代 strict 指标。

本轮 scaled-manifest retry 是当前 manifest 下的第一份 observed prediction-only model evidence。它不是 paired training evidence，因为 source adapter 仍来自旧的 `public-sample-20260617T045941Z` train split。当前结论是 no strict recovery / partial signal：dev/test exact 分别是 `0.2464` / `0.2029`，schema、route 和 safety recall 稳定，但 strict slot F1 和 full-contract exact 明显偏低。

先前 current-train-split retry 的 trade-off diagnosis 进一步确认：dev safety recovered `4` rows / safety regressed `0` rows，但 confirmation regressed `5` dev rows 和 `2` test rows；dev exact 是 `2` recovered / `4` regressed，test exact 是 `7` recovered / `3` regressed。该 prior-manifest dominant trade-off 是 `confirmation_regression_after_safety_recovery`，其后续 confirmation-preservation design / materialization 已完成；当前最新诊断边界以上方 scaled-manifest residual diagnosis 为准。

随后完成的 confirmation-preservation candidate design 将这个 trade-off 收束成 `2` 个 reviewable families：`unsafe_payment_confirmation_preservation` 覆盖 `5` 个 dev `blocked_payment` source rows，要求保留 `blocked/deny`、`unsafe_payment` 和 `confirmation_required=true`；`public_navigation_non_confirmation_preservation` 覆盖 `2` 个 test navigation source rows，要求保留 `navigate/open_url`、`public_readonly` 和 `confirmation_required=false`。这是 design-only evidence，没有 materialize seed rows、没有训练、没有 prediction，也不能宣称模型恢复。

最新的 scaled public-sample / tiered-eval design 将下一阶段方向从窄修窄训切换为先扩数据设计和分层诊断：当前边界仍是 `102` seeds / `261` SFT rows / `881` DPO pairs / `123` train rows，设计目标是 review 后走向 `240` seed milestone，并把评估拆成 schema、task/route、safety/confirmation、strict slot、full-contract exact 五层。它仍是 design-only evidence，没有 materialize seed rows、没有训练、没有 prediction、没有改 evaluator。主指标仍是 `contract_exact_match` 和 strict `slot_f1`；`slot_f1_soft` 只做诊断。

随后已完成 standalone scaled public-sample candidate materialization：

- evidence: `reports/public-sample/scaled-public-sample-candidate-materialization/scaled_public_sample_candidate_materialization.md`
- candidate seed file: `data/public-samples/scaled_public_sample_seed_candidates.jsonl`
- 新增 `138` 条 standalone candidate seeds，其中 `118` 条 core family delta candidates、`20` 条 confirmation-boundary overlay candidates；
- 派生 `414` 条 SFT candidate rows；
- 随后已通过独立 formal merge phase 合入新的 public sample boundary；
- 没有生成 DPO pairs、没有训练、没有 prediction、没有改 prompt/evaluator、没有 slot normalization、没有 prediction repair，也不能宣称模型恢复。

随后已完成 scaled public-sample formal merge：

- evidence: `reports/public-sample/scaled-public-sample-merge/scaled_public_sample_public_sample_merge.md`
- new manifest: `public-sample-20260617T152259Z`
- formal public sample 已更新为 240 seeds / 675 SFT rows / 2046 DPO pairs；
- split counts 更新为 train 261 / dev 207 / test 207；
- 合入 `138` 条 reviewed scaled candidate seeds，并保留原 train/dev/test split labels；
- 该阶段没有训练、没有 prediction、没有 A100 execution、没有改 prompt/evaluator、没有 slot normalization，也不能宣称模型恢复；
- 因为 formal public sample boundary 已改变，旧 metrics 不能直接和未来新 boundary metrics 比较。

## 已完成的项目价值

1. 项目定位已收束：这是 `voice-browser-agent` 的 post-training companion，负责把中文语音指令或 ASR transcript 转成严格 schema 的 browser task contract。
2. 数据和评估链路已成型：public sample、manifest、SFT/DPO builders、prediction-only held-out、metrics、diagnostics、leak scan 和 OpenSpec archives 都有可追溯产物。
3. 模型输出形态稳定：当前 formal public dev/test 的 `json_valid_rate` 都是 1.0000，说明 schema-valid JSON 已不是主要风险。
4. 证据边界更可信：当前报告不再用旧 dev128 / SFT v2 指标做 headline，而是以 formal public held-out 的 strict 指标为准。

## 仍然存在的风险

1. Full-contract exact match 仍未恢复：scaled-manifest dev/test 为 0.2464 / 0.2029，离 strict recovery 很远。
2. Strict slot exactness 是当前最大残差来源：scaled residual diagnosis 记录 `slots=304` 个 strict residual fields。
3. `normalized_command` strict string mismatch 也很重：scaled residual diagnosis 记录 `normalized_command=194` 个 residual fields。
4. Route/task_type、safety、confirmation 相对更稳定，但仍有少量 residual fields：`task_type=13`、`route=13`、`safety=10`、`confirmation_required=6`。
5. `clarify/slots=78` 已经进入 target selection、candidate design 和 standalone materialization，但还没有 formal merge、重训或生成新 prediction；不能把候选数据说成模型效果提升。

## 不应过度宣称

- 不是 production readiness。
- 不是 held-out recovery。
- 不是 checkpoint 或 LoRA adapter release。
- 不是 private-corpus generalization。
- 不是 public full-corpus release。
- 不是 live-browser benchmark improvement。
- 不是 evaluator relaxation 或 semantic-equivalence recovery。

## 推荐下一阶段

当前最新推荐来自 `materialize-canonical-slot-boundary-row-level-candidates`：

- 输入：`data/public-samples/canonical_slot_boundary_seed_candidates.jsonl`、
  `reports/public-sample/canonical-slot-boundary-row-level-candidates/manifest.json`、
  `reports/public-sample/canonical-slot-boundary-row-level-candidates/canonical_slot_boundary_row_level_candidate_materialization.json` 和
  `reports/public-sample/canonical-slot-boundary-candidate-review/summary.json`；
- 推荐下一步：单独开 formal merge review/apply phase，检查该 row-level source 是否可进入 formal public sample；
- 目的：评审并显式决定是否合并这 7 条 canonical slot-boundary candidates；当前阶段没有 direct merge；
- 边界：不要在本阶段 formal merge、训练、重跑 prediction、改 evaluator、slot repair、
  prediction repair、DPO/GRPO、LoRA/base-model 调整、LLM judge、semantic-equivalence
  scoring 或 deterministic postprocessor implementation；
- 后续：若要 formal sample merge，必须再开新的 bounded OpenSpec change，运行 public-safe
  validation、duplicate/source-id validation、derived SFT/DPO/manifest synchronization、
  split-boundary accounting，并明确 comparison boundary。

不建议直接启动 paired SFT retry，也不建议把 normalized/layered metrics 说成
held-out recovery。

## 历史 prior-manifest 阶段

formal held-out residual-family diagnosis 和 target selection 已经补完并归档到先前 manifest 边界。

当前诊断结论：

- residual-family diagnosis 绑定 `public-sample-20260616T074315Z`，共有 97 strict residual rows；
- residual-cluster inspection 的 top cluster 仍是 `form_fill` / `normalized_command`；
- target selection 选择 `form_fill`，对应 29 residual rows / 49 residual fields；
- confirmation-marker coverage 只刷新当前 residual evidence 指针，保留旧 policy / materialized candidate 的历史来源，避免循环血缘。

随后已完成 `form_fill` SFT v3 readiness 阶段：

- readiness evidence: `reports/public-sample/form-fill-remediation-sft-v3-readiness/form_fill_remediation_sft_v3_readiness.md`
- dry-run 选择当前 public train split 的 114 条 SFT rows；
- 其中包含 21 条已合入 train split 的 form-fill remediation / confirmation-marker rows；
- readiness status 是 `ready_for_bounded_a100_sft_v3_phase`；
- 这个阶段没有训练、没有 prediction rerun、没有改数据、没有改 evaluator。

随后已完成独立的 SFT v3 retry phase：

- evidence: `reports/public-sample/a100-form-fill-remediation-sft-v3-retry-after-ssh-recovery/report.md`
- fresh A100 preflight 后选择空闲 GPU；
- 创建 repo-external private override；
- 训练 private SFT v3 adapter，使用当前 public train split 的 114 条 rows；
- dev/test 各生成 69 条 prediction，并用 strict evaluator 评估；
- 导入 public-safe metrics / predictions / sidecars / manifest / report；
- 未发布 adapter、checkpoint、raw log、private override、远端缓存或私有路径。

这批 prior SFT v3 retry 是后续 current-manifest prediction-only baseline 的
adapter 来源之一；当时模型效果以上方 current-train-split SFT retry 指标为准。
随后已完成 bounded safety / `blocked_payment` regression diagnosis：

- evidence: `reports/public-sample/sft-v3-safety-regression-diagnosis/sft_v3_safety_regression_diagnosis.md`
- 诊断只读取 baseline/retry 的 gold 与 predictions，没有训练、没有生成新 prediction、没有改数据、没有改 evaluator；
- 当前 formal dev/test 共有 21 个 gold-stop rows，其中 18 个属于 `blocked_payment`；
- SFT v3 retry 新增 1 条 dev `blocked_payment` regression；
- 另有 3 条 dev `blocked_payment` persistent misses 是 baseline 与 retry 都漏掉的安全 false negative；
- test split 恢复了 1 条 prior `blocked_payment` miss。

下一步不是改 evaluator、重跑 DPO 或直接再训练，而是开一个 bounded
`blocked_payment` safety repair candidate design phase，在 materialize 新数据
或训练前先定义哪些支付确认/退款/扣款表述必须 route 到 `blocked/deny`。

随后已完成 `blocked_payment` safety repair candidate design：

- evidence: `reports/public-sample/blocked-payment-safety-repair-candidate-design/blocked_payment_safety_repair_candidate_design.md`
- 该阶段只从 safety regression diagnosis 派生 reviewable candidate design，没有写 seed rows、没有生成 DPO pairs、没有改 public sample、没有训练、没有 prediction；
- 设计出 2 个 repair families：`refund_confirmation_or_processing` 覆盖 3 条 source rows，`subscription_charge_confirmation` 覆盖 1 条 source row；
- accepted target sketch 均为 `task_type=blocked`、`route=deny`、`safety.allow=false`、`safety.reason=unsafe_payment`；
- rejected drift sketch 覆盖 baseline 的 `clarify/clarify` 漂移和 retry 的 `form_fill/fill_form` 漂移。

下一步如果继续，应开 bounded materialization phase，把这 2 个 reviewed
repair candidates 转成 public-safe seed rows，并重新生成 public sample derived
artifacts；仍然不能从 candidate design 本身宣称 safety improvement 或模型恢复。

随后已完成 bounded `blocked_payment` safety repair materialization：

- materialization evidence: `reports/public-sample/blocked-payment-safety-repair-materialization/blocked_payment_safety_repair_materialization.md`
- public merge evidence: `reports/public-sample/blocked-payment-safety-repair-public-sample-merge/blocked_payment_safety_repair_public_sample_merge.md`
- 当时的 public sample boundary 更新为 `public-sample-20260616T165835Z`；
- counts 从 98 seeds / 252 SFT rows / 850 DPO pairs 变为 100 seeds / 256 SFT rows / 864 DPO pairs；
- 新增 2 条 train seed rows，对应 `refund_confirmation_or_processing` 和 `subscription_charge_confirmation`；
- 新增 4 条 SFT rows 和 14 条 DPO construction pairs；
- 该阶段没有训练、没有 prediction、没有改 evaluator、没有 claim safety improvement 或 model recovery。

随后已完成 current-manifest SFT v3 prediction-only baseline：

- evidence: `reports/public-sample/a100-current-manifest-sft-v3-prediction-baseline/report.md`
- fresh A100 preflight 后选择空闲 GPU；
- 使用已有 private SFT v3 adapter，不训练；
- dev/test 各生成 69 条 prediction，并用 strict evaluator 评估；
- evidence 记录 `source_adapter_runtime=a100-form-fill-remediation-sft-v3` 和 `dataset_manifest_id=public-sample-20260616T165835Z`；
- 指标与 prior SFT v3 retry 一致，因为 blocked-payment repair 新增 rows 只进入 train split；
- 该阶段没有训练、没有 prediction repair、没有改 evaluator、没有发布 adapter/checkpoint，也没有 claim safety improvement 或 model recovery。

随后已完成 current 118-row train split 的 SFT retry readiness / retry-design：

- evidence: `reports/public-sample/current-train-split-sft-retry-readiness/current_train_split_sft_retry_readiness.md`
- 本地 dry-run 选择全部 118 条 train rows；
- train split 中包含 21 条 form-fill repair rows 和 4 条 blocked-payment repair rows；
- 新增独立 future runtime label：`a100-current-train-split-sft-retry`；
- readiness status: `ready_for_bounded_a100_sft_retry_phase`；
- 该阶段没有训练、没有 prediction、没有改数据、没有改 prompt/evaluator、没有发布 adapter/checkpoint，也没有 claim safety improvement 或 model recovery。

随后已完成独立的 `run-a100-current-train-split-sft-retry` phase：

- evidence: `reports/public-sample/a100-current-train-split-sft-retry/report.md`
- fresh A100 preflight 后选择空闲 GPU 3；
- 创建 repo-external private override；
- 训练 private adapter，使用当前 public train split 的 118 条 rows；
- dev/test 各生成 69 条 prediction，并用 strict evaluator 评估；
- 导入 public-safe metrics / predictions / sidecars / manifest / report；
- 未发布 adapter、checkpoint、raw log、private override、远端缓存或私有路径。

随后已完成 current-train-split SFT retry trade-off diagnosis：

- evidence: `reports/public-sample/current-train-split-sft-retry-tradeoff-diagnosis/current_train_split_sft_retry_tradeoff_diagnosis.md`
- 该阶段只读取 current-manifest baseline 与 current-train-split retry 的 gold / predictions / metrics；
- 没有训练、没有生成新 prediction、没有改数据、没有改 prompt/evaluator、没有发布 adapter/checkpoint；
- dev safety recovered `4` rows 且 safety regressions 为 `0`；
- confirmation regressed `5` dev rows 和 `2` test rows；
- exact movement mixed：dev `2` recovered / `4` regressed，test `7` recovered / `3` regressed；
- dominant trade-off: `confirmation_regression_after_safety_recovery`。

当前结果仍是 mixed partial signal：安全 false negative 被修复，但 confirmation 与 exact/route 仍有 trade-off。下一步如果继续，应打开 bounded `design-current-retry-confirmation-preservation-candidates` phase，先设计可审阅的 confirmation-preservation seed / target sketches，而不是直接继续训练、改 evaluator 或引入 DPO。

随后已完成 current-retry confirmation-preservation candidate design：

- evidence: `reports/public-sample/current-retry-confirmation-preservation-candidate-design/current_retry_confirmation_preservation_candidate_design.md`
- 该阶段只读取 current retry trade-off diagnosis 与同 manifest 的 baseline/retry gold/predictions；
- 没有 materialize seed rows、没有生成 SFT/DPO rows、没有 rebuild manifest、没有训练、没有 prediction、没有改 prompt/evaluator；
- 设计出 2 个 candidate families，合计覆盖 7 个 source rows；
- `unsafe_payment_confirmation_preservation` 覆盖 5 个 dev `blocked_payment` rows，accepted target 保留 `blocked/deny`、`unsafe_payment`、`confirmation_required=true`；
- `public_navigation_non_confirmation_preservation` 覆盖 2 个 test navigation rows，accepted target 保留 `navigate/open_url`、`public_readonly`、`confirmation_required=false`。

随后已完成 current-retry confirmation-preservation materialization：

- materialization evidence: `reports/public-sample/current-retry-confirmation-preservation-materialization/current_retry_confirmation_preservation_materialization.md`
- public merge evidence: `reports/public-sample/current-retry-confirmation-preservation-public-sample-merge/current_retry_confirmation_preservation_public_sample_merge.md`
- 当前 public sample 已更新为 `public-sample-20260617T045941Z`；
- counts 从 100 seeds / 256 SFT rows / 864 DPO pairs 变为 102 seeds / 261 SFT rows / 881 DPO pairs；
- 新增 2 条 train seed rows，对应 `unsafe_payment_confirmation_preservation` 和 `public_navigation_non_confirmation_preservation`；
- 新增 5 条 SFT rows 和 17 条 DPO construction pairs；
- 该阶段没有训练、没有 prediction、没有改 prompt/evaluator、没有 slot normalization、没有 claim safety improvement 或 model recovery。

当时的下一步是先在新 manifest 边界下做 bounded prediction-only baseline 或 training-readiness，避免把这次 data materialization 直接包装成模型效果改善。

随后已完成 current-123-row train-split SFT retry readiness：

- evidence: `reports/public-sample/current-123-train-split-sft-retry-readiness/current_train_split_sft_retry_readiness.md`
- 该阶段只做本地 dry-run 和 public-safe readiness report；
- 没有 A100 training、prediction、DPO、prompt/evaluator 改动、slot normalization、checkpoint/adapter 发布或 private corpus 发布；
- dry-run 选择全部 123 条 train rows；
- train split 中包含 21 条 form-fill repair rows、4 条 blocked-payment repair rows、5 条 current-retry confirmation-preservation rows；
- readiness status: `ready_for_bounded_a100_sft_retry_phase`；
- prediction configs 被明确标注为需要 paired adapter trained for `public-sample-20260617T045941Z`，不能直接拿 prior adapter 结果当作 current-manifest model evidence。

随后已完成 current-123-row train-split A100 SFT retry：

- evidence: `reports/public-sample/a100-current-123-train-split-sft-retry/report.md`
- fresh A100 preflight 后选择空闲 GPU；
- 创建 repo-external private override；
- 训练 private adapter，使用当前 public train split 的 123 条 rows；
- dev/test 各生成 69 条 prediction，并用 strict evaluator 评估；
- 导入 public-safe metrics / predictions / sidecars / manifest / report；
- 未发布 adapter、checkpoint、raw log、private override、远端缓存或私有路径。

当前 scaled-boundary 结果不是 strict recovery：dev/test exact 为 `0.2464` /
`0.2029`，strict slot F1 为 `0.2874` / `0.2593`，safety recall 均为 `1.0000`。
当前最新下一步应是 bounded residual-family / tiered diagnosis，明确定位 scaled
manifest 上 exact 和 slot 下跌来自哪些 family / field，再决定是否需要 paired
SFT retry；不应直接继续训练、改 evaluator、引入 DPO 或宣称模型恢复。

随后已完成 scaled current-123 adapter residual-cluster inspection：

- evidence: `reports/public-sample/scaled-current-123-adapter-residual-cluster-inspection/formal_heldout_residual_cluster_inspection.md`
- 该阶段只读取已提交的 scaled residual-family diagnosis；
- 没有 A100 job、training、prediction、data mutation、prompt/evaluator 改动、slot normalization、prediction repair、adapter/checkpoint 发布或 recovery claim；
- `321` 个 residual rows / `540` 个 residual fields 被聚合成 `29` 个 ranked clusters；
- 最大 cluster 是 `clarify/slots`，对应 `clarify|clarify|ambiguous_request|confirm:true|slots:ambiguity`，`78` rows / `78` fields；
- 后续高位 clusters 是 `blocked/slots`、`search/slots`、`form_fill/slots` 和 `blocked/normalized_command`。

随后已完成 scaled residual remediation target selection：

- evidence: `reports/public-sample/scaled-residual-remediation-target-selection/scaled_residual_remediation_target_selection.md`
- 该阶段只读取 cluster inspection evidence；
- 没有 A100 job、training、prediction、data materialization、dataset mutation、prompt/evaluator 改动、slot normalization、prediction repair、adapter/checkpoint 发布或 recovery claim；
- 选择 `clarify/slots` 作为第一修复目标；
- `blocked/slots` 被明确 defer 到 dedicated safety boundary phase，不视为已解决；
- 推荐下一步是 `design-scaled-clarify-slot-boundary-candidates`，先设计 clarify ambiguity slot / route-intent 边界案例或策略，不应泛化扩数据或直接训练。

## 主要证据链接

- Latest paired SFT comparison: `reports/public-sample/canonical-slot-paired-sft-ablation/comparison.md`
- Latest paired SFT comparison JSON: `reports/public-sample/canonical-slot-paired-sft-ablation/comparison.json`
- Latest paired SFT boundary verification: `reports/public-sample/canonical-slot-paired-sft-ablation/boundary-verification.json`
- Latest paired SFT control training summary: `reports/public-sample/canonical-slot-paired-sft-ablation/control/training_summary.json`
- Latest paired SFT treatment training summary: `reports/public-sample/canonical-slot-paired-sft-ablation/treatment/training_summary.json`
- Latest paired SFT control metrics: `reports/public-sample/canonical-slot-paired-sft-ablation/control/dev/metrics.md` and `reports/public-sample/canonical-slot-paired-sft-ablation/control/test/metrics.md`
- Latest paired SFT treatment metrics: `reports/public-sample/canonical-slot-paired-sft-ablation/treatment/dev/metrics.md` and `reports/public-sample/canonical-slot-paired-sft-ablation/treatment/test/metrics.md`
- Latest evidence report: `reports/public-sample/a100-scaled-public-sample-current-123-adapter-prediction-baseline-after-a100-recovery/report.md`
- Prior current-123 adapter evidence report: `reports/public-sample/a100-current-123-train-split-sft-retry/report.md`
- Latest scaled public-sample merge: `reports/public-sample/scaled-public-sample-merge/scaled_public_sample_public_sample_merge.md`
- Latest canonical slot-boundary formal merge: `reports/public-sample/canonical-slot-boundary-formal-merge/canonical_slot_boundary_public_sample_merge.md`
- Latest scaled residual-cluster inspection: `reports/public-sample/scaled-current-123-adapter-residual-cluster-inspection/formal_heldout_residual_cluster_inspection.md`
- Latest residual-driven remediation target selection: `reports/public-sample/remediation-target-selection/summary.md`
- Latest scaled residual remediation target selection: `reports/public-sample/scaled-residual-remediation-target-selection/scaled_residual_remediation_target_selection.md`
- Latest canonical slot-boundary formal-merge proposal/readiness: `reports/public-sample/canonical-slot-boundary-formal-merge-proposal/summary.md`
- Latest scaled candidate materialization: `reports/public-sample/scaled-public-sample-candidate-materialization/scaled_public_sample_candidate_materialization.md`
- Latest scaled candidate seed file: `data/public-samples/scaled_public_sample_seed_candidates.jsonl`
- Latest scaled public-sample / tiered-eval design: `reports/public-sample/scaled-public-sample-and-tiered-eval-design/scaled_public_sample_and_tiered_eval_design.md`
- Latest confirmation-preservation candidate design: `reports/public-sample/current-retry-confirmation-preservation-candidate-design/current_retry_confirmation_preservation_candidate_design.md`
- Latest trade-off diagnosis: `reports/public-sample/current-train-split-sft-retry-tradeoff-diagnosis/current_train_split_sft_retry_tradeoff_diagnosis.md`
- Latest Dev metrics: `reports/public-sample/a100-scaled-public-sample-current-123-adapter-prediction-baseline-after-a100-recovery/dev/metrics.md`
- Latest Test metrics: `reports/public-sample/a100-scaled-public-sample-current-123-adapter-prediction-baseline-after-a100-recovery/test/metrics.md`
- Current-manifest prediction-only baseline: `reports/public-sample/a100-current-manifest-sft-v3-prediction-baseline/report.md`
- Prior SFT v3 retry after SSH recovery: `reports/public-sample/a100-form-fill-remediation-sft-v3-retry-after-ssh-recovery/report.md`
- Baseline evidence report: `reports/public-sample/a100-formal-public-heldout-prediction-after-a100-recovery/report.md`
- Current manifest: `data/public-samples/manifest_public_sample.json`
- Residual-family diagnosis: `reports/public-sample/formal-heldout-residual-family-diagnosis/formal_heldout_residual_family_diagnosis.md`
- Residual-cluster inspection: `reports/public-sample/formal-heldout-residual-cluster-inspection/formal_heldout_residual_cluster_inspection.md`
- Target selection: `reports/public-sample/formal-heldout-remediation-target-selection/formal_heldout_remediation_target_selection.md`
- SFT v3 readiness: `reports/public-sample/form-fill-remediation-sft-v3-readiness/form_fill_remediation_sft_v3_readiness.md`
- SFT v3 blocked preflight: `reports/public-sample/a100-form-fill-remediation-sft-v3/preflight_blocked.md`
- SFT v3 retry after SSH recovery: `reports/public-sample/a100-form-fill-remediation-sft-v3-retry-after-ssh-recovery/report.md`
- SFT v3 safety regression diagnosis: `reports/public-sample/sft-v3-safety-regression-diagnosis/sft_v3_safety_regression_diagnosis.md`
- Blocked-payment repair candidate design: `reports/public-sample/blocked-payment-safety-repair-candidate-design/blocked_payment_safety_repair_candidate_design.md`
- Blocked-payment repair materialization: `reports/public-sample/blocked-payment-safety-repair-materialization/blocked_payment_safety_repair_materialization.md`
- Blocked-payment repair public merge: `reports/public-sample/blocked-payment-safety-repair-public-sample-merge/blocked_payment_safety_repair_public_sample_merge.md`
- Current-retry confirmation-preservation materialization: `reports/public-sample/current-retry-confirmation-preservation-materialization/current_retry_confirmation_preservation_materialization.md`
- Current-retry confirmation-preservation public merge: `reports/public-sample/current-retry-confirmation-preservation-public-sample-merge/current_retry_confirmation_preservation_public_sample_merge.md`
- Current-123 train split SFT retry readiness: `reports/public-sample/current-123-train-split-sft-retry-readiness/current_train_split_sft_retry_readiness.md`
- Current train split SFT retry readiness: `reports/public-sample/current-train-split-sft-retry-readiness/current_train_split_sft_retry_readiness.md`
- Context contract: `CONTEXT.md`
- Human brief: `docs/human-briefs/2026-06-16-refresh-current-formal-heldout-residual-diagnosis.html`
- Human brief (SFT v3 readiness): `docs/human-briefs/2026-06-16-assess-form-fill-remediation-sft-v3-readiness.html`
- Human brief (SFT v3 blocked): `docs/human-briefs/2026-06-16-run-a100-form-fill-remediation-sft-v3.html`
- Human brief (SFT v3 retry): `docs/human-briefs/2026-06-16-retry-a100-form-fill-remediation-sft-v3-after-ssh-recovery.html`
- Human brief (SFT v3 safety regression diagnosis): `docs/human-briefs/2026-06-16-diagnose-sft-v3-safety-regression.html`
- Human brief (blocked-payment repair candidate design): `docs/human-briefs/2026-06-16-design-blocked-payment-safety-repair-candidates.html`
- Human brief (blocked-payment repair materialization): `docs/human-briefs/2026-06-16-materialize-blocked-payment-safety-repair-candidates.html`
- Human brief (current-manifest SFT v3 prediction baseline): `docs/human-briefs/2026-06-17-run-current-manifest-sft-v3-prediction-baseline.html`
- Human brief (current train split SFT retry readiness): `docs/human-briefs/2026-06-17-assess-current-train-split-sft-retry-readiness.html`
- Human brief (current train split SFT retry): `docs/human-briefs/2026-06-17-run-a100-current-train-split-sft-retry.html`
- Human brief (current train split SFT retry trade-off diagnosis): `docs/human-briefs/2026-06-17-diagnose-current-train-split-sft-retry-tradeoffs.html`
- Human brief (current retry confirmation-preservation candidate design): `docs/human-briefs/2026-06-17-design-current-retry-confirmation-preservation-candidates.html`
- Human brief (current retry confirmation-preservation materialization): `docs/human-briefs/2026-06-17-materialize-current-retry-confirmation-preservation-candidates.html`
- Human brief (scaled public sample and tiered eval design): `docs/human-briefs/2026-06-17-design-scaled-public-sample-and-tiered-eval.html`
- Human brief (scaled public sample candidate materialization): `docs/human-briefs/2026-06-17-materialize-scaled-public-sample-candidates.html`
- Human brief (scaled public sample merge): `docs/human-briefs/2026-06-17-merge-scaled-public-sample-candidates.html`
- Human brief (scaled current-123 adapter residual diagnosis): `docs/human-briefs/2026-06-18-diagnose-scaled-current-123-adapter-residuals.html`
- Human brief (scaled current-123 adapter residual cluster inspection): `docs/human-briefs/2026-06-18-inspect-scaled-current-123-adapter-residual-clusters.html`
- Human brief (scaled residual remediation target selection): `docs/human-briefs/2026-06-18-select-scaled-residual-remediation-target.html`
- Human brief (residual-driven remediation target selection): `docs/human-briefs/2026-06-18-select-residual-driven-remediation-target.html`
- Human brief (safety repair candidate design): `docs/human-briefs/2026-06-18-design-safety-repair-candidates.html`
- Human brief (safety repair candidate design review): `docs/human-briefs/2026-06-18-review-safety-repair-candidates-before-materialization.html`
- Human brief (slot canonicalization policy): `docs/human-briefs/2026-06-18-design-slot-canonicalization-policy.html`
- Human brief (canonical slot-boundary candidate review): `docs/human-briefs/2026-06-18-review-canonical-slot-boundary-candidates-before-merge.html`
- Human brief (canonical slot-boundary formal-merge proposal/readiness): `docs/human-briefs/2026-06-19-propose-canonical-slot-boundary-formal-merge-after-review.html`
- Human brief (canonical slot-boundary formal merge): `docs/human-briefs/2026-06-19-merge-canonical-slot-boundary-row-level-candidates.html`
- Human brief (canonical slot paired SFT ablation): `docs/human-briefs/2026-06-20-run-canonical-slot-paired-sft-ablation.html`

## 当前交付状态

可以作为阶段性交付收束：代码、public sample、OpenSpec archives、A100 prediction-only baseline、residual diagnosis / target selection、SFT v3 readiness、SFT v3 blocked preflight evidence、SFT v3 retry evidence、SFT v3 safety regression diagnosis、blocked-payment repair candidate design、blocked-payment repair materialization、current-manifest SFT v3 prediction-only baseline、current-train-split SFT retry readiness、current-train-split SFT retry、current-train-split retry trade-off diagnosis、current-retry confirmation-preservation candidate design、current-retry confirmation-preservation materialization、scaled public-sample / tiered-eval design、scaled public-sample candidate materialization、scaled public-sample formal merge、A100 recovery prediction-only retry、scaled residual-family diagnosis、scaled residual-cluster inspection、scaled residual remediation target selection、layered evaluator、residual diagnosis、residual-driven remediation target selection、safety repair candidate design、safety repair candidate design review、slot canonicalization policy、canonical slot-boundary candidate materialization、canonical slot-boundary candidate review、canonical slot-boundary formal-merge proposal/readiness、canonical slot-boundary row-level candidate materialization、canonical slot-boundary formal merge、canonical slot paired SFT ablation、Human Brief、最终状态说明都已经对齐到明确边界。最新 paired SFT ablation 是 SFT-only positive partial signal，但 pilot gate 未通过；如继续，应进入 `design-and-implement-contract-v2`，而不是直接追加少量 canonical candidates、运行 DPO、宣称 held-out recovery、训练收益、evaluator 改进、postprocessor 效果或模型恢复。
