# Voice2Task Post-Training 实验报告

> Superseded: 这份报告保留为历史实验说明。当前项目收束结论请以
> `reports/final_status.md` 和
> `reports/public-sample/a100-formal-public-heldout-prediction-after-a100-recovery/report.md`
> 为准。

## 一句话结论

当前最可信结论来自 formal public sample 的 prediction-only held-out 证据：7B LoRA 路径可以稳定输出 schema-valid contract JSON，但严格 full-contract exact match 仍然是 partial signal（dev 0.3043 / test 0.2899），不能宣称 held-out recovery、生产可用、checkpoint/adapter 发布或 live-browser benchmark 提升。

## 当前权威证据

| 项目 | 值 |
| --- | --- |
| Evidence pack | `reports/public-sample/a100-formal-public-heldout-prediction/` |
| Manifest | `public-sample-20260615T111316Z` |
| Public sample | 77 seeds / 231 SFT rows / 661 DPO pairs |
| Split | train 93 / dev 69 / test 69 |
| Run type | prediction-only held-out evaluation |
| Boundary | no training, no data mutation, no evaluator relaxation, no prediction repair |

### Formal Public Held-Out 指标

| 指标 | Dev | Test |
| --- | ---: | ---: |
| rows | 69 | 69 |
| json_valid_rate | 1.0000 | 1.0000 |
| task_type_accuracy | 0.8551 | 0.9130 |
| route_accuracy | 0.8551 | 0.9130 |
| safety_precision | 1.0000 | 0.9167 |
| safety_recall | 0.6667 | 0.9167 |
| confirmation_accuracy | 0.9855 | 1.0000 |
| slot_f1 (strict) | 0.3913 | 0.5072 |
| slot_f1_soft (internal diagnostic) | 0.7315 | 0.7609 |
| contract_exact_match | 0.3043 | 0.2899 |

`contract_exact_match` 和 strict `slot_f1` 是主指标。`slot_f1_soft` 只用于内部误差定位，不能替代 strict 指标，也不能把语义相近的 slot 表述自动算作恢复。

## 历史实验位置

旧的 full-corpus / dev128 SFT v2 实验说明了训练、预测、评估链路能跑通，也帮助定位 slot value 表述差异，但它不再是当前项目 headline。

| 历史配置 | Split | contract_exact_match | slot_f1 (strict) | slot_f1_soft |
| --- | --- | ---: | ---: | ---: |
| SFT v2 normalized | dev128 | 0.133 | 0.330 | 0.703 |
| SFT v2 normalized | test160 | 0.169 | 0.430 | 0.668 |

这些结果来自旧数据边界，适合作为 pipeline diagnostic，不适合作为当前 formal public held-out 结论。

## 关键发现

1. **结构化格式已经不是主要风险。** 当前 formal public dev/test 的 `json_valid_rate` 都是 1.0000，说明输出 schema 形态稳定。

2. **full-contract held-out 仍然偏弱。** `contract_exact_match` dev/test 分别为 0.3043 / 0.2899，说明真实瓶颈在合约字段整体一致性，而不是单纯 JSON 格式。

3. **残差不只来自 slot wording。** route/task_type dev/test 为 0.8551 / 0.9130，safety recall dev/test 为 0.6667 / 0.9167；下一阶段应先做 residual family diagnosis。

4. **soft slot_f1 只能解释现象。** soft 指标高于 strict 指标，说明中文 query 表述差异确实存在，但 public claim 仍以 strict metrics 为准。

5. **DPO 不是当前优先方向。** 之前 DPO 对 slot exactness 没有解决作用；在没有残差家族诊断前继续 DPO 容易扩大错误假设。

## 推荐下一阶段

下一阶段建议做一个很小的 OpenSpec 阶段：formal public held-out residual/family diagnosis。

目标是逐行检查 dev/test residual，按 family、field path、mismatch category 汇总，回答：

- route/task_type 错误是否集中在 clarify、extract、form_fill 或其他边界家族；
- safety recall 低的样本是否集中在 blocked-payment 场景；
- strict slot_f1 的低分有多少来自 key mismatch、value wording、缺 slot 或多 slot；
- 是否真的需要新数据、prompt policy、训练，还是只是报告/标注边界需要调整。

在完成诊断前，不建议直接扩数据、重训、重跑 DPO、修改 evaluator 或提高 public claim。

## 证据链接

- Current formal report: `reports/public-sample/a100-formal-public-heldout-prediction/report.md`
- Dev metrics: `reports/public-sample/a100-formal-public-heldout-prediction/dev/metrics.md`
- Test metrics: `reports/public-sample/a100-formal-public-heldout-prediction/test/metrics.md`
- Public manifest: `data/public-samples/manifest_public_sample.json`
- Current README: `README.md`
- Current English README: `README_en.md`

## Claims Not To Overstate

- 不是 production readiness。
- 不是 checkpoint 或 LoRA adapter release。
- 不是 private-corpus generalization。
- 不是 live-browser benchmark improvement。
- 不是 evaluator relaxation 或 semantic-equivalence recovery。
- 不是 held-out recovery；除非 dev/test strict `contract_exact_match` 都达到 1.0，否则只能称为 partial held-out signal。
