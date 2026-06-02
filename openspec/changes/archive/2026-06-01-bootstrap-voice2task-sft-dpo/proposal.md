## Why

Voice2Task Post-Training should turn the existing Voice-to-Browser Agent speech-to-task evidence into a focused post-training project rather than another generic chat fine-tuning demo. The first phase needs a reproducible SFT/DPO loop that maps Chinese spoken commands or ASR transcripts into safe, schema-valid browser task contracts and evaluates those contracts with product-relevant metrics.

## What Changes

- Introduce a first-phase Voice2Task training pipeline for speech-to-contract normalization.
- Build train/dev/test data from sanitized Voice-to-Browser Agent seed traces, public samples, schema-preserving augmentation, and hard negative pairs.
- Add supervised contract tuning for Qwen-family small instruction models using Transformers, PEFT, and TRL as the primary transparent stack.
- Add preference contract tuning with DPO pairs that prefer safer, more executable, and less ambiguous browser task contracts.
- Add a contract evaluation ladder covering schema validity, task type, route, safety, confirmation, slots, and execution smoke.
- Publish sanitized sample data, dataset builders, manifests, and aggregate reports while keeping the full local/private corpus out of git.
- Non-goals: generic chat fine-tuning, Hermes-style skill routing, GUI action policy learning, first-phase GRPO/rule-reward training, public release of the full local corpus, and claims of live-browser benchmark improvement before evidence exists.

## Capabilities

### New Capabilities

- `voice2task-dataset-preparation`: Build public sample and local/private train/dev/test corpora for speech-to-contract normalization.
- `supervised-contract-tuning`: Run SFT LoRA experiments that teach small Qwen-family models to emit schema-valid browser task contracts.
- `preference-contract-tuning`: Run DPO experiments over chosen/rejected browser task contracts.
- `contract-evaluation`: Evaluate model outputs with schema, route, safety, confirmation, slot, and execution-smoke metrics.

### Modified Capabilities

- None.

## Impact

- Adds a new OpenSpec-managed training/evaluation project under this repository.
- Adds dataset builders, public sample data, local/private artifact conventions, training configs/scripts, evaluation scripts, and reports.
- Adds Python ML dependencies around Transformers, PEFT, TRL, datasets, accelerate, and optional ms-swift integration for later engineering runs.
- Uses Voice-to-Browser Agent as the source of sanitized seed traces and the downstream execution-smoke target, but does not move training ownership into that runtime repository.
