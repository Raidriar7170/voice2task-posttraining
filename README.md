# Voice2Task Post-Training

Voice2Task Post-Training is a bounded companion repo for turning Chinese spoken browser commands or ASR transcripts into safe, schema-valid browser task contracts. The first phase covers dataset construction, SFT/DPO formatting, dry-run training metadata, contract metrics, and public-safe reports.

It is not a generic chat fine-tuning project, not a GUI action policy learner, and not a released-checkpoint claim. The committed data is a small public sample for inspection and smoke tests; full local/private corpora stay under gitignored artifact directories.

## Quickstart

```bash
PYTHONPATH=src python -m voice2task.cli.data build-public \
  --seed data/public-samples/seed_traces.jsonl \
  --output data/public-samples

PYTHONPATH=src python -m voice2task.cli.data validate \
  --sft data/public-samples/sft_public_sample.jsonl \
  --dpo data/public-samples/dpo_public_sample.jsonl \
  --manifest data/public-samples/manifest_public_sample.json \
  --public

PYTHONPATH=src python -m voice2task.cli.eval baseline \
  --gold data/public-samples/sft_public_sample.jsonl \
  --output reports/public-sample/rule_baseline_predictions.jsonl

PYTHONPATH=src python -m voice2task.cli.eval prompt-baseline \
  --gold data/public-samples/sft_public_sample.jsonl \
  --fixture reports/public-sample/rule_baseline_predictions.jsonl \
  --output reports/public-sample/prompt_fixture_predictions.jsonl

PYTHONPATH=src python -m voice2task.cli.eval metrics \
  --gold data/public-samples/sft_public_sample.jsonl \
  --predictions reports/public-sample/rule_baseline_predictions.jsonl \
  --output reports/public-sample

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

Heavy training is opt-in. `--run-training` checks the real TRL/PEFT entrypoint, but configs must set
`allow_heavy_training: true` before any model download or training run starts.

## A100 Public-Sample SFT Smoke Runbook

This workflow is a bounded execution smoke for the committed public sample, not full private-corpus
training and not a checkpoint release. Confirm model download permission, remote runtime access, idle GPU
selection, and output placement before running it. Keep all generated checkpoints, adapters, caches, and
raw logs outside git.

Use the dedicated smoke config:

```bash
PYTHONPATH=src python -m voice2task.cli.train sft \
  --config configs/sft-a100-public-smoke.json \
  --manifest data/public-samples/manifest_public_sample.json \
  --output-dir <a100_project_root>/runs/a100-sft-public-smoke \
  --run-training
```

The committed config is a public-safe template. On the A100 machine, create a private override that
resolves `<a100_project_root>` to the approved project root before running heavy training. The config
sets `allow_heavy_training: true`, but the command still requires `--run-training`; either opt-in
missing, or an unresolved template root, keeps the workflow from starting heavy training. Public repo
evidence is limited to sanitized metadata, aggregate metrics, controlled smoke status, leak-scan
status, and the public-safe report under `reports/public-sample/a100-sft-smoke/`.

## Artifact Boundaries

- `data/public-samples/`: committed sanitized seed traces, generated public SFT rows, DPO pairs, and public manifest.
- `data/local-private/`: gitignored full local/private corpora built from configured Voice-to-Browser Agent seed trace exports.
- `configs/`: small local/dev and larger A100 config templates for Qwen-family LoRA SFT/DPO runs.
- `reports/public-sample/`: committed aggregate metrics, dry-run metadata, and reviewer-safe sample reports.
- `reports/generated-local/` and `reports/private/`: gitignored local reports that may summarize private corpora.
- `adapters/`, `checkpoints/`, `runs/`, and `logs/`: gitignored training outputs.

## Scope Boundaries

The first-phase model capability is speech-to-contract normalization: emit canonical browser task contract JSON from Chinese spoken commands or ASR transcripts. It does not route arbitrary skills, choose browser actions, publish a full private corpus, promise GRPO/rule-reward training, or claim live-browser benchmark improvement.

Training commands in this bootstrap phase default to dry-run metadata export. They record the intended TRL/PEFT stack, base model, dataset manifest, hyperparameters, and adapter output path without downloading models. The real SFT/DPO code path is present behind an explicit `--run-training` plus config opt-in so validation cannot accidentally start a heavy run. The DPO bootstrap path initializes from the configured base model and records `sft_model_ref` as metadata; adapter-continuation DPO can be scoped as a later change.
