# Voice2Task Post-Training

[中文](README.md) | [English](README_en.md)

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Status](https://img.shields.io/badge/status-final%20lockbox%20reported-0b6e69)
![Model](https://img.shields.io/badge/model-Qwen2.5--7B%20LoRA-6f42c1)
![Scope](https://img.shields.io/badge/scope-evidence--first-f59e0b)

Voice2Task 是一个中文 spoken command / ASR transcript 到浏览器任务合约的
post-training 项目。
核心模型任务不是直接控制浏览器，而是把用户口语命令转换成严格的
Browser Task Contract JSON，供后续浏览器 agent 决定搜索、打开 URL、
填写表单、抽取页面信息、澄清或拒绝高风险动作。

## Controlled Browser Demo MVP

本仓库现在包含一个可选的、面向中文语音入口的可验证受控 Browser Agent Demo：`fixture inference + disabled ASR + localhost sandbox execution`。它复用 `BrowserTaskContract V1`，通过 `202 Accepted` 后台生命周期、静态 capability、可恢复的一次性 challenge、两阶段确认/执行、Playwright exact-origin 隔离和独立 action/DOM evidence 演示六条公开场景。

```bash
python -m pip install -e '.[demo,dev]'
python -m playwright install chromium
make demo
```

[运行说明、架构、截图与严格非声明边界](docs/demo/README.md) · [六场景 benchmark](reports/demo-mvp/summary.md)

该 Demo 只证明受控 fixture 编排，不证明通用 Agent、真实互联网泛化、自然语音/ASR 泛化、模型质量、生产级或已上线。默认不加载私有 adapter，不访问 lockbox，不运行训练。

## Recruiter Summary

| Area | What this project built |
| --- | --- |
| Problem | 中文语音/ASR 浏览器命令 -> schema-valid browser task contract JSON |
| Model pipeline | Qwen2.5-7B-Instruct + LoRA SFT；adapter 私有，不随仓库发布 |
| Data/training | 247 seeds / 696 SFT rows / 2,100 preference pairs；public dev/test 为 `DEVELOPMENT_ONLY_SPENT`；final SFT 只使用既有训练数据 |
| Prompt/eval hardening | 统一 gold-free prompt policy `unified_gold_free_v1`；严格 JSON parse -> strict schema -> semantic contract -> exact match 分层验证 |
| Frozen evaluation | 120-row `lockbox-v1`，120 semantic families，manifest frozen，one-look final evaluation |
| Result boundary | final SFT 没有提升 strict contract exact match；`no overall model improvement claim` |

## Final Lockbox v1 Result

Frozen protocol:
`lockbox_hash=06114cf3ad6029930284af5f2245fb2c4a8174fd35c6a1107f4c73482b555b33`,
prompt policy `unified_gold_free_v1`, greedy decoding,
schema guard + one schema retry, strict evaluator,
two pre-registered arms only.

| Metric | Base Qwen2.5-7B | Final SFT adapter | Delta |
| --- | ---: | ---: | ---: |
| `contract_exact_match` | 0.0167 | 0.0083 | -0.0083 |
| `semantic_contract_valid_rate` | 0.8250 | 0.8667 | +0.0417 |
| `task_type_accuracy` | 0.7917 | 0.8583 | +0.0667 |
| `route_accuracy` | 0.8000 | 0.8583 | +0.0583 |
| `confirmation_accuracy` | 0.7083 | 0.7917 | +0.0833 |
| `strict_schema_valid_rate` | 1.0000 | 0.9833 | -0.0167 |
| `slot_f1` | 0.0417 | 0.0500 | +0.0083 |
| `slot_f1_soft` | 0.3783 | 0.3867 | +0.0084 |

Interpretation:

- Final SFT did **not** improve strict contract exact match on the frozen lockbox.
- Final SFT did improve several semantic/channel metrics:
  `semantic_contract_valid_rate +0.0417`, `task_type_accuracy +0.0667`,
  `route_accuracy +0.0583`, `confirmation_accuracy +0.0833`.
- This is aggregate-only one-look evidence. Public reports do not include row-level failure analysis；不能据此推断 row-level failure cause、natural-ASR generalization 或 overall SFT causal effect。

Evidence links:

- [Final comparison JSON](reports/lockbox-v1/final-evaluation/comparison.json)
- [Final run card](reports/lockbox-v1/final-evaluation/run-card.json)
- [Final comparison Markdown](reports/lockbox-v1/final-evaluation/comparison.md)
- [Current status and evidence](docs/current-status.md)
- [Lockbox protocol](docs/lockbox.md)

## Explicit Non-Claims

This repository does **not** claim:

- overall model improvement from final SFT (`no overall model improvement claim`);
- production readiness;
- safety readiness;
- executable browser quality;
- DPO success;
- adapter/checkpoint release;
- live-browser benchmark improvement.

The strongest supported claim is narrower:
under a frozen 120-row lockbox and a gold-free strict evaluator,
final SFT improved several semantic/channel aggregate metrics
but reduced strict full-contract exact match.

## Repository Role

| This repo is | This repo is not |
| --- | --- |
| A speech/ASR-to-contract post-training evidence repository | A generic chat fine-tuning project |
| A strict JSON contract generation and evaluation pipeline | A GUI action policy or browser controller |
| A public-safe SFT/DPO data, training, prediction, and evaluation workflow | A checkpoint or adapter release |
| A place where negative, blocked, and superseded evidence stays auditable | A success story built by deleting inconvenient results |

## Method Overview

1. Build public-safe Voice2Task data from seed traces into SFT and preference rows.
2. Render Qwen chat prompts with no gold contract in prediction prompts.
3. Train LoRA SFT adapters on existing training data only.
4. Decode greedily with `max_new_tokens=256`, schema guard enabled, and at most one schema retry.
5. Score with strict layered metrics: JSON parse, strict schema validity,
   semantic contract validity, exact match, slot-level metrics,
   route/task/confirmation/safety metrics.
6. Freeze lockbox rows and manifest before the final one-look evaluation.

## Quick Start

Install local tooling:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev,dataset]'
```

Rebuild and validate the committed public sample:

```bash
PYTHONPATH=src python -m voice2task.cli.data build-public \
  --seed data/public-samples/seed_traces.jsonl \
  --output data/public-samples

PYTHONPATH=src python -m voice2task.cli.data validate \
  --sft data/public-samples/sft_public_sample.jsonl \
  --dpo data/public-samples/dpo_public_sample.jsonl \
  --manifest data/public-samples/manifest_public_sample.json \
  --public

PYTHONPATH=src python -m voice2task.cli.data audit-splits \
  --seed data/public-samples/seed_traces.jsonl \
  --sft data/public-samples/sft_public_sample.jsonl \
  --dpo data/public-samples/dpo_public_sample.jsonl \
  --manifest data/public-samples/manifest_public_sample.json \
  --output reports/public-sample/split-integrity-audit
```

Run local baselines and metrics:

```bash
PYTHONPATH=src python -m voice2task.cli.eval baseline \
  --gold data/public-samples/sft_public_sample.jsonl \
  --output reports/public-sample/rule_baseline_predictions.jsonl

PYTHONPATH=src python -m voice2task.cli.eval metrics \
  --gold data/public-samples/sft_public_sample.jsonl \
  --predictions reports/public-sample/rule_baseline_predictions.jsonl \
  --output reports/public-sample
```

Dry-run training metadata export remains available, but real heavy training is gated by explicit config:

```bash
PYTHONPATH=src python -m voice2task.cli.train sft \
  --config configs/sft-dev.json \
  --manifest data/public-samples/manifest_public_sample.json \
  --output-dir reports/public-sample/sft-dry-run \
  --dry-run

PYTHONPATH=src python -m voice2task.cli.train dpo \
  --config configs/dpo-dev.json \
  --manifest data/public-samples/manifest_public_sample.json \
  --output-dir reports/public-sample/dpo-dry-run \
  --dry-run
```

## Metric Interpretation Boundaries

`contract_exact_match` is a hard full-contract exact-match metric. Future evaluator runs use recursive JSON type-strict equality: booleans, integers, and floating-point values are distinct; object key order and serialization whitespace are ignored; array order is preserved; non-finite or non-JSON values fail closed. Historical metrics were not re-scored.
`normalized_command` string-mismatch diagnostics are explanatory row-level
evidence only: they do not relax, normalize, semantically score, repair, replace,
or re-score predictions, and they do not automatically mark Chinese phrase differences such as `搜索/查询` or `明天的天气/明天天气` as equivalent.

`normalized_command` gold targets are canonical Chinese intent phrases, not
verbatim transcripts or ASR text. This is target-writing guidance for SFT/DPO
data and prompts, not evaluator-side normalization, semantic-equivalence
scoring, prediction repair, or re-scoring.

### Normalized Command Target Policy

Targets use canonical Chinese intent phrases, not verbatim transcripts or ASR
text. Representative forms include `搜索北京明天天气`, `打开示例网站`,
`填写邮箱并确认`, and `拒绝代替用户付款`. This is authoring guidance, not
evaluator-side normalization or semantic-equivalence scoring.

## Evidence Archive

Longer-running internal evidence remains documented below the headline result:

- Public split integrity: the current 282/207/207 dev/test boundary is
  `DEVELOPMENT_ONLY_SPENT`, not blind, independent, leakage-free, or
  final-generalization evidence. The audit preserves historical rows and
  metrics; lockbox-v1 remains the distinct frozen one-look aggregate boundary.
- Contract V2 projection: `PARTIAL_SCHEMA_BENEFIT`; derived-field-only strict
  failures are 14.65%, normalized-command-only strict failures are 14.65%, and
  core slot failures remain 68.79% of V1 strict failures. This is useful
  schema-burden evidence, not model-quality evidence.
- Copy-backed verification and shadow mode: observe-only provenance/interface evidence, not runtime enforcement.
- Copy-shadow template-disjoint challenge v1: adversarial verifier fixture, not a naturalistic language benchmark.
- Earlier step-matched SFT ablations: mixed/inconclusive; no stable broad canonical-slot benefit.

See [current status](docs/current-status.md) and
[public evidence index](reports/public-sample/EVIDENCE_INDEX.md) for the
complete archived map.

## A100 Boundary

GPU-heavy training and prediction are designed for a private A100 development
machine.
Public repo artifacts intentionally omit checkpoints, LoRA adapters, raw logs,
remote caches, private corpus rows, hostnames, SSH details, credentials,
private paths, private override configs, and production-readiness claims.

## Validation

Useful local checks:

```bash
PYTHONPATH=src pytest -q
PYTHONPATH=src ruff check src tests
OPENSPEC_TELEMETRY=0 openspec validate --all --strict
PYTHONPATH=src python scripts/check_current_truth_surface.py
git diff --check
```

## License

本项目采用 [MIT License](LICENSE)。
