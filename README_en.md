# Voice2Task Post-Training

[中文](README.md) | [English](README_en.md)

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Status](https://img.shields.io/badge/status-current%20evidence-0b6e69)
![Model](https://img.shields.io/badge/model-Qwen2.5--7B%20LoRA-6f42c1)
![Scope](https://img.shields.io/badge/scope-evidence--first-f59e0b)

Voice2Task Post-Training is an evidence-first project for Chinese voice-to-browser task contracts. Its narrow task is to turn Chinese spoken commands or ASR transcripts into schema-valid browser task contract JSON, then keep the public sample, manifests, reports, OpenSpec archives, and Human Briefs clear about what the evidence does and does not prove.

## Current Snapshot

| Item | Current public status |
|---|---|
| Task | Chinese spoken / ASR browser commands -> schema-valid browser task contracts |
| Model | Qwen2.5-7B-Instruct + LoRA; private adapters are not released |
| Dataset | 247 seeds / 696 SFT rows / 2,100 preference pairs |
| Evaluation | Schema validity, strict contract exact match, slot-level analysis, and step-matched ablation |
| Current conclusion | Training gains remain mixed and statistically inconclusive; provenance verification remains observe-only. No model-improvement, executable-quality, safety-readiness, or production-readiness claim is made. |
| Contract V2 status | Projection decision is `PARTIAL_SCHEMA_BENEFIT`; derived-field-only strict failures are 14.65%, normalized-command-only strict failures are 14.65%, and core slot failures remain 68.79% of V1 strict failures. |
| Copy-shadow status | Challenge v1 is an adversarial verifier fixture, not a naturalistic benchmark. False-trust diagnosis is `SOURCE_ATTESTATION_HARDENED_SCOPE_REDUCTION_REQUIRED`; Policy V2 design is `POLICY_V2_SCOPE_REDUCTION_READY_FOR_REVIEW`; source-attested-but-gold-mismatch count is 16, normalization-collision downgrades are 6, and execution-eligible count is 0. |

[Detailed current status and evidence ->](docs/current-status.md)

## Repository Role

| This repo is | This repo is not |
| --- | --- |
| A speech/ASR-to-contract post-training evidence repository | A generic chat fine-tuning project |
| A strict JSON contract generation and evaluation pipeline | A GUI action policy or browser controller |
| A public-safe SFT/DPO data, training, prediction, and evaluation workflow | A checkpoint or adapter release |
| A place where negative, blocked, and superseded evidence stays auditable | A success story built by deleting inconvenient results |

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

`contract_exact_match` is a hard full-contract exact-match metric. `normalized_command` string-mismatch diagnostics are explanatory row-level evidence only: they do not relax, normalize, semantically score, repair, replace, or re-score predictions, and they do not automatically mark Chinese phrase differences such as `搜索/查询` or `明天的天气/明天天气` as equivalent.

## Normalized Command Target Policy

`normalized_command` gold targets are canonical Chinese intent phrases, not verbatim transcripts or ASR text. First-phase public samples use concise target phrases such as `搜索北京明天天气`, `打开示例网站`, `填写邮箱并确认`, and `拒绝代替用户付款`; schema-preserving paraphrases keep the same target contract. This is target-writing guidance for SFT/DPO data and prompts, not evaluator-side normalization, semantic-equivalence scoring, prediction repair, or re-scoring.

## A100 Boundary

GPU-heavy training and prediction are designed for a private A100 development machine. Public repo artifacts intentionally omit checkpoints, LoRA adapters, raw logs, remote caches, private corpus rows, hostnames, SSH details, credentials, private paths, private override configs, and production-readiness claims.

## Validation

Useful local checks:

```bash
PYTHONPATH=src pytest -q
PYTHONPATH=src ruff check src tests
OPENSPEC_TELEMETRY=0 openspec validate --all --strict
python scripts/check_current_truth_surface.py
git diff --check
PYTHONPATH=src python scripts/run_copy_backed_prediction_shadow_hook_review.py
```

## License

This project is licensed under the [MIT License](LICENSE).
