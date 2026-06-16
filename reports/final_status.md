# Voice2Task 最终状态说明

更新日期：2026-06-16

## 一句话结论

当前项目可以收束为一个证据完整、边界清楚的 Voice2Task post-training / evaluation baseline：链路能稳定产出 schema-valid contract JSON，但 formal public held-out 上仍是 partial signal，不能宣称生产可用、held-out recovery、checkpoint/adapter 发布或 live-browser benchmark 提升。

## 当前权威证据

| 项目 | 值 |
| --- | --- |
| Latest evidence pack | `reports/public-sample/a100-form-fill-remediation-sft-v3-retry-after-ssh-recovery/` |
| Baseline evidence pack | `reports/public-sample/a100-formal-public-heldout-prediction-after-a100-recovery/` |
| Manifest | `public-sample-20260616T074315Z` |
| Public sample | 98 seeds / 252 SFT rows / 850 DPO pairs |
| Split | train 114 / dev 69 / test 69 |
| Latest run type | private A100 SFT v3 on public train split + dev/test prediction |
| Latest interpretation | `form_fill_sft_v3_partial_improvement_with_safety_regression_risk` |

最新 SFT v3 retry 在当前 manifest 上训练了一个 private A100 adapter，然后重新跑 dev/test prediction。它没有改数据、没有修 prediction、没有 normalize slot，也没有放松 evaluator；adapter、checkpoint、raw log、private override 和远端缓存都没有发布。

## Formal Public Held-Out 指标

| 指标 | Dev | Test |
| --- | ---: | ---: |
| rows | 69 | 69 |
| json_valid_rate | 1.0000 | 1.0000 |
| task_type_accuracy | 0.8696 | 0.9275 |
| route_accuracy | 0.8696 | 0.9275 |
| safety_precision | 1.0000 | 0.9231 |
| safety_recall | 0.5556 | 1.0000 |
| confirmation_accuracy | 0.9710 | 0.9855 |
| slot_f1 (strict) | 0.5652 | 0.4976 |
| slot_f1_soft (diagnostic only) | 0.8157 | 0.7646 |
| contract_exact_match | 0.4638 | 0.3478 |

主指标是 `contract_exact_match` 和 strict `slot_f1`。`slot_f1_soft` 只能说明 slot value 存在表述相近但 exact 不一致的现象，不能替代 strict 指标。

相对 prediction-only baseline：dev exact `+0.1594`、dev strict slot_f1 `+0.1739`；test exact `+0.0580`、test strict slot_f1 `-0.0097`。同时 dev safety_recall 从 `0.6667` 降到 `0.5556`，这是下一阶段必须优先诊断的风险。

## 已完成的项目价值

1. 项目定位已收束：这是 `voice-browser-agent` 的 post-training companion，负责把中文语音指令或 ASR transcript 转成严格 schema 的 browser task contract。
2. 数据和评估链路已成型：public sample、manifest、SFT/DPO builders、prediction-only held-out、metrics、diagnostics、leak scan 和 OpenSpec archives 都有可追溯产物。
3. 模型输出形态稳定：当前 formal public dev/test 的 `json_valid_rate` 都是 1.0000，说明 schema-valid JSON 已不是主要风险。
4. 证据边界更可信：当前报告不再用旧 dev128 / SFT v2 指标做 headline，而是以 formal public held-out 的 strict 指标为准。

## 仍然存在的风险

1. Full-contract exact match 仍未恢复：dev/test 为 0.4638 / 0.3478，明显好于 baseline，但离 strict recovery 很远。
2. Route/task_type 仍有边界问题：dev/test 为 0.8696 / 0.9275，错误仍集中在边界家族。
3. Safety recall 出现 dev 回退：dev 从 0.6667 降到 0.5556，不能用 test 的 1.0000 掩盖 false negative 风险。
4. Slot exactness 仍是残差来源：dev slot failure 30 条，test slot failure 38 条；soft 指标只能辅助定位，不能对外过度表达。

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

因此当前模型效果应以本报告上方的 SFT v3 retry 指标为准：它是局部改善，
不是 held-out recovery。下一步不是改 evaluator 或重跑 DPO，而是开一个
bounded safety / `blocked_payment` regression diagnosis phase，解释 dev
safety_recall 回退并决定是否需要更窄的数据或 policy 修复。

## 主要证据链接

- Latest evidence report: `reports/public-sample/a100-form-fill-remediation-sft-v3-retry-after-ssh-recovery/report.md`
- Latest Dev metrics: `reports/public-sample/a100-form-fill-remediation-sft-v3-retry-after-ssh-recovery/dev/metrics.md`
- Latest Test metrics: `reports/public-sample/a100-form-fill-remediation-sft-v3-retry-after-ssh-recovery/test/metrics.md`
- Baseline evidence report: `reports/public-sample/a100-formal-public-heldout-prediction-after-a100-recovery/report.md`
- Current manifest: `data/public-samples/manifest_public_sample.json`
- Residual-family diagnosis: `reports/public-sample/formal-heldout-residual-family-diagnosis/formal_heldout_residual_family_diagnosis.md`
- Residual-cluster inspection: `reports/public-sample/formal-heldout-residual-cluster-inspection/formal_heldout_residual_cluster_inspection.md`
- Target selection: `reports/public-sample/formal-heldout-remediation-target-selection/formal_heldout_remediation_target_selection.md`
- SFT v3 readiness: `reports/public-sample/form-fill-remediation-sft-v3-readiness/form_fill_remediation_sft_v3_readiness.md`
- SFT v3 blocked preflight: `reports/public-sample/a100-form-fill-remediation-sft-v3/preflight_blocked.md`
- SFT v3 retry after SSH recovery: `reports/public-sample/a100-form-fill-remediation-sft-v3-retry-after-ssh-recovery/report.md`
- Context contract: `CONTEXT.md`
- Human brief: `docs/human-briefs/2026-06-16-refresh-current-formal-heldout-residual-diagnosis.html`
- Human brief (SFT v3 readiness): `docs/human-briefs/2026-06-16-assess-form-fill-remediation-sft-v3-readiness.html`
- Human brief (SFT v3 blocked): `docs/human-briefs/2026-06-16-run-a100-form-fill-remediation-sft-v3.html`
- Human brief (SFT v3 retry): `docs/human-briefs/2026-06-16-retry-a100-form-fill-remediation-sft-v3-after-ssh-recovery.html`

## 当前交付状态

可以作为阶段性交付收束：代码、public sample、OpenSpec archives、A100 prediction-only baseline、residual diagnosis / target selection、SFT v3 readiness、SFT v3 blocked preflight evidence、SFT v3 retry evidence、Human Brief、最终状态说明都已经对齐到同一套边界。下一步如果继续，应优先诊断 SFT v3 后的 safety / `blocked_payment` 回退，而不是从当前报告直接启动无边界训练。
