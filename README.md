# Voice2Task Post-Training

[中文](README.md) | [English](README_en.md)

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Status](https://img.shields.io/badge/status-current%20evidence-0b6e69)
![Model](https://img.shields.io/badge/model-Qwen2.5--7B%20LoRA-6f42c1)
![Scope](https://img.shields.io/badge/scope-evidence--first-f59e0b)

Voice2Task Post-Training 是一个证据优先的中文语音到浏览器任务合约微调项目。目标很窄：把 Chinese spoken command / ASR transcript 转成 schema-valid browser task contract JSON，并用公开安全的 sample、manifest、report、OpenSpec archive 和 Human Brief 说明证据边界。

## Current Snapshot

- Task: Chinese spoken / ASR browser commands -> schema-valid browser task contracts.
- Model path: Qwen2.5-7B-Instruct + LoRA; private A100 adapters are observed but not released.
- Current formal sample: `public-sample-20260619T090925Z`; 247 seeds / 696 SFT rows / 2100 DPO pairs; train/dev/test = 282/207/207.
- Latest training experiment: one-seed step-matched canonical-slot SFT ablation with 3132 optimizer steps per arm.
- Training conclusion: mixed / statistically inconclusive; no stable general canonical-data benefit.
- Latest architecture experiment: Contract V2 offline projection with recovered step-matched inputs.
- Projection conclusion: `PARTIAL_SCHEMA_BENEFIT`.
- Derived-field-only strict failures: 14.65%; normalized-command-only strict failures: 14.65%; metadata-only failures: 0%.
- V2 core exact: small improvement, +0.0193 / +0.0386 for Control dev/test and +0.0290 / +0.0242 for Treatment dev/test.
- V2 executable pass: no improvement.
- Dominant bottleneck: core slot failures remain about 68.79% of V1 strict failures.
- Renderer check: normalized-command renderer support is 99.88%; deterministic roundtrip is 1.0.
- Projection follow-up `decide-contract-v2-core-implementation-scope` is closed as an internal implementation boundary.
- Internal Contract V2 Core: `INTERNAL_V2_CORE_READY_RENDERER_PARTIAL`; preserve_legacy V1 roundtrip, safety, confirmation, and slots all remain 1.0; V1 evaluator metric deltas are all 0.
- Internal derive_display support is 99.77%, with 5 unsupported renderer cases; it is not the default path.
- Completed internal-core recommendation: `analyze-slot-error-mechanisms-and-design-slot-representation`.
- Slot mechanism analysis: `MIXED_SLOT_REPRESENTATION_REQUIRED`; exact/normalized source-copyable gold slots 50.53%; typed-derivable slots 0.00%; generation-required slots 49.47%; prediction unsupported-by-source 32.17%.
- Hybrid slot representation design: `HYBRID_DESIGN_READY_COPY_SLICE_FIRST`; overall representation coverage 100.00%; copy-backed coverage 57.32%; bounded structured coverage 31.21%; unresolved coverage 11.46%; current predictions deterministically verifiable at 51.80% and fail-closed at 48.20%.
- Copy-backed slot verification slice: `COPY_SLICE_READY_FOR_SHADOW_INTEGRATION`; enabled triples are `extract:extract_page:target`, `form_fill:fill_form:field`, and `search:search_web:query`; gold unique verified span rate is 86.38%; Control/Treatment source-verified prediction rate over eligible events is 87.44%; provenance false accepts and silent fallbacks are 0.
- Copy-backed verification shadow mode: `SHADOW_MODE_READY_FOR_REVIEW`; 828/828 current Control/Treatment prediction contracts have shadow sidecars; enforcement enabled count is 0; action source-verified count is 0; V1 evaluator metric deltas remain 0.
- Copy-backed shadow interface review: `SHADOW_INTERFACE_READY_FOR_PREDICTION_HOOK`; online sidecars are gold-free for 828/828 prediction contracts; evaluation audit rows are 942; trusted exact rate is 87.44%; eligible verification failure rate is 12.56%; out-of-scope rate is 54.35%; trusted-exact gold mismatch rate is 7.71%; false accepts, silent fallbacks, contract mutations, runtime deltas, normalized trusted cases, and action trusted cases are all 0.
- Current recommendation: `integrate-copy-backed-verification-prediction-shadow-hook`, still shadow-only and no runtime enforcement.

No model weights changed during the Contract V2 projection, slot mechanism analysis, hybrid slot representation design, copy-backed verification slice, shadow-mode integration, or shadow interface review. strict exact remains canonical diagnostic. Prior metrics are historical unless marked `CURRENT` in the evidence index.

## Current Evidence

| Evidence | Current conclusion |
| --- | --- |
| [`reports/public-sample/contract-v2-projection/rerun-with-recovered-inputs/summary.json`](reports/public-sample/contract-v2-projection/rerun-with-recovered-inputs/summary.json) | Current Contract V2 projection result: `PARTIAL_SCHEMA_BENEFIT`. |
| [`reports/public-sample/internal-contract-v2-core/summary.json`](reports/public-sample/internal-contract-v2-core/summary.json) | Internal Contract V2 Core boundary is V1-compatible in preserve mode; derive_display remains partial. |
| [`reports/public-sample/slot-error-mechanism-analysis/summary.json`](reports/public-sample/slot-error-mechanism-analysis/summary.json) | Slot mechanism analysis result: `MIXED_SLOT_REPRESENTATION_REQUIRED`; next change is `design-hybrid-slot-representation-v1`. |
| [`reports/public-sample/hybrid-slot-representation-v1/summary.json`](reports/public-sample/hybrid-slot-representation-v1/summary.json) | Hybrid representation design result: `HYBRID_DESIGN_READY_COPY_SLICE_FIRST`; next change is `implement-copy-backed-slot-verification-slice`. |
| [`reports/public-sample/copy-backed-slot-verification-slice/summary.json`](reports/public-sample/copy-backed-slot-verification-slice/summary.json) | Copy-backed verification slice result: `COPY_SLICE_READY_FOR_SHADOW_INTEGRATION`; sidecar-only provenance for task-scoped `query`/`field`/`target`. |
| [`reports/public-sample/copy-backed-verification-shadow-mode/summary.json`](reports/public-sample/copy-backed-verification-shadow-mode/summary.json) | Shadow-mode integration result: `SHADOW_MODE_READY_FOR_REVIEW`; one sidecar per current prediction contract, no enforcement. |
| [`reports/public-sample/copy-backed-shadow-mode-review/summary.json`](reports/public-sample/copy-backed-shadow-mode-review/summary.json) | Shadow interface review result: `SHADOW_INTERFACE_READY_FOR_PREDICTION_HOOK`; gold-free online sidecars, offline audit split, no enforcement. |
| [`reports/public-sample/step-matched-canonical-slot-ablation/comparison.json`](reports/public-sample/step-matched-canonical-slot-ablation/comparison.json) | Latest model experiment: mixed / inconclusive; no stable broad canonical-slot benefit. |
| [`data/public-samples/manifest_public_sample.json`](data/public-samples/manifest_public_sample.json) | Current formal sample boundary: 247 seeds / 696 SFT rows / 2100 DPO pairs. |
| [`reports/public-sample/EVIDENCE_INDEX.md`](reports/public-sample/EVIDENCE_INDEX.md) | Unified current / historical / superseded / blocked / design-only / raw-input / archived evidence map. |

## Claim Boundaries

Current evidence cannot claim model improvement. It cannot claim executable quality improvement. It cannot claim production readiness. It cannot claim safety readiness. It cannot claim held-out recovery. It cannot claim live-browser benchmark gain. It cannot claim checkpoint release. It cannot claim adapter release. It cannot claim DPO justification. It cannot claim another canonical-candidate loop.

The Contract V2 projection is offline schema-burden evidence only: it removes derived/display-field burden from strict exact comparison, but it does not claim model improvement. The internal Contract V2 Core boundary now exists behind a V1-compatible deterministic envelope; it does not change the public V1 schema, V1 evaluator, training target, predictions, or downstream runtime. The slot mechanism analysis and hybrid slot representation design are read-only/design-only evidence. The copy-backed verification slice, shadow-mode integration, and shadow interface review are provenance/interface evidence only: source-backed provenance is not task correctness, slot accuracy, executable quality, runtime enforcement, production readiness, or proof that an online hook already exists.

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
```

## License

The package metadata declares an MIT license. A standalone `LICENSE` file should be added before presenting the repository as an open-source release.
