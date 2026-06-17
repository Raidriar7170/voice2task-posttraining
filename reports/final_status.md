# Voice2Task 最终状态说明

更新日期：2026-06-18

## 一句话结论

当前项目可以收束为一个证据完整、边界清楚的 Voice2Task post-training / evaluation baseline：链路能稳定产出 schema-valid contract JSON，但 formal public held-out 上仍是 partial signal，不能宣称生产可用、held-out recovery、checkpoint/adapter 发布或 live-browser benchmark 提升。

## 当前权威证据

| 项目 | 值 |
| --- | --- |
| Latest data evidence pack | `reports/public-sample/scaled-public-sample-merge/` |
| Latest scaled-manifest prediction baseline evidence pack | `reports/public-sample/a100-scaled-public-sample-current-123-adapter-prediction-baseline-after-a100-recovery/` |
| Prior blocked scaled-manifest baseline evidence pack | `reports/public-sample/a100-scaled-public-sample-current-123-adapter-prediction-baseline/` |
| Latest standalone scaled candidate evidence pack | `reports/public-sample/scaled-public-sample-candidate-materialization/` |
| Latest readiness evidence pack | `reports/public-sample/current-123-train-split-sft-retry-readiness/` |
| Latest model evidence pack | `reports/public-sample/a100-scaled-public-sample-current-123-adapter-prediction-baseline-after-a100-recovery/` |
| Prior current-123 model evidence pack | `reports/public-sample/a100-current-123-train-split-sft-retry/` |
| Latest strategic-design evidence pack | `reports/public-sample/scaled-public-sample-and-tiered-eval-design/` |
| Latest candidate-design evidence pack | `reports/public-sample/current-retry-confirmation-preservation-candidate-design/` |
| Latest diagnosis evidence pack | `reports/public-sample/current-train-split-sft-retry-tradeoff-diagnosis/` |
| Baseline evidence pack | `reports/public-sample/a100-formal-public-heldout-prediction-after-a100-recovery/` |
| Current data manifest | `public-sample-20260617T152259Z` |
| Current public sample | 240 seeds / 675 SFT rows / 2046 DPO pairs |
| Current split | train 261 / dev 207 / test 207 |
| Latest evaluated manifest | `public-sample-20260617T152259Z` |
| Latest evaluated public sample | 240 seeds / 675 SFT rows / 2046 DPO pairs |
| Latest run type | prediction-only retry on the scaled dev/test split using the existing `a100-current-train-split-sft-retry` private adapter |
| Latest interpretation | `formal_public_heldout_partial_signal` |
| Latest strategic-design interpretation | `scale_data_and_diagnose_by_tier_before_another_training_retry` |
| Latest diagnosis interpretation | `current_sft_retry_tradeoff_diagnosis_confirmation_regression_after_safety_recovery` |
| Prior SFT v3 retry evidence | `reports/public-sample/a100-form-fill-remediation-sft-v3-retry-after-ssh-recovery/` |

最新模型证据绑定 `public-sample-20260617T152259Z`。它是 A100 恢复后的 prediction-only retry：使用已有的 private `a100-current-train-split-sft-retry` adapter，在 scaled dev/test split 上生成预测并用 strict evaluator 评估。没有训练、没有修 prediction、没有 normalize slot、没有改 prompt、没有放松 evaluator。adapter、checkpoint、raw log、private override 和远端缓存都没有发布。

注意比较边界：这个 adapter 的训练来源是 `public-sample-20260617T045941Z`，而本次评估目标是 `public-sample-20260617T152259Z`。因此这份结果是新 scaled boundary 下的 baseline，不是和旧 current-123 指标的 clean improvement/regression comparison。

此前第一次 scaled-manifest prediction-only baseline 尝试仍作为 historical blocked evidence 保留：

- evidence: `reports/public-sample/a100-scaled-public-sample-current-123-adapter-prediction-baseline/report.md`
- status: blocked before A100 prediction because the configured SSH alias timed out

A100 恢复后已完成 observed retry：

- evidence: `reports/public-sample/a100-scaled-public-sample-current-123-adapter-prediction-baseline-after-a100-recovery/report.md`
- target manifest: `public-sample-20260617T152259Z`
- source adapter runtime: `a100-current-train-split-sft-retry`
- source adapter manifest: `public-sample-20260617T045941Z`
- status: observed, prediction-only, no training

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

随后完成的 trade-off diagnosis 进一步确认：dev safety recovered `4` rows / safety regressed `0` rows，但 confirmation regressed `5` dev rows 和 `2` test rows；dev exact 是 `2` recovered / `4` regressed，test exact 是 `7` recovered / `3` regressed。当前 dominant trade-off 是 `confirmation_regression_after_safety_recovery`，下一阶段应先设计 confirmation-preservation candidates，而不是直接继续训练或调整 evaluator。

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

1. Full-contract exact match 仍未恢复：dev/test 为 0.4348 / 0.3768，离 strict recovery 很远。
2. Route/task_type 仍有边界问题：dev/test 为 0.8841 / 0.9275。
3. Slot exactness 仍是残差来源：dev slot failure 31 条，test slot failure 34 条；soft 指标只能辅助定位，不能对外过度表达。
4. 仍需要 residual / trade-off diagnosis 才能判断下一次数据设计目标，不能直接从本轮 retry 推出继续训练方向。

## 不应过度宣称

- 不是 production readiness。
- 不是 held-out recovery。
- 不是 checkpoint 或 LoRA adapter release。
- 不是 private-corpus generalization。
- 不是 public full-corpus release。
- 不是 live-browser benchmark improvement。
- 不是 evaluator relaxation 或 semantic-equivalence recovery。

## 推荐下一阶段

formal held-out residual-family diagnosis 和 target selection 已经补完并归档到最新 manifest。

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
adapter 来源之一；最新模型效果以上方 current-train-split SFT retry 指标为准。
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

## 主要证据链接

- Latest evidence report: `reports/public-sample/a100-scaled-public-sample-current-123-adapter-prediction-baseline-after-a100-recovery/report.md`
- Prior current-123 adapter evidence report: `reports/public-sample/a100-current-123-train-split-sft-retry/report.md`
- Latest scaled public-sample merge: `reports/public-sample/scaled-public-sample-merge/scaled_public_sample_public_sample_merge.md`
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

## 当前交付状态

可以作为阶段性交付收束：代码、public sample、OpenSpec archives、A100 prediction-only baseline、residual diagnosis / target selection、SFT v3 readiness、SFT v3 blocked preflight evidence、SFT v3 retry evidence、SFT v3 safety regression diagnosis、blocked-payment repair candidate design、blocked-payment repair materialization、current-manifest SFT v3 prediction-only baseline、current-train-split SFT retry readiness、current-train-split SFT retry、current-train-split retry trade-off diagnosis、current-retry confirmation-preservation candidate design、current-retry confirmation-preservation materialization、scaled public-sample / tiered-eval design、scaled public-sample candidate materialization、scaled public-sample formal merge、A100 recovery prediction-only retry、Human Brief、最终状态说明都已经对齐到明确边界。下一步如果继续，应先开 bounded scaled-manifest residual-family / tiered diagnosis，再考虑 paired-adapter training；不应直接继续训练、改 evaluator、引入 DPO 或宣称模型恢复。
