# Voice2Task Lockbox v1 Final SFT Prep Run Card

Status: final SFT adapter trained, non-lockbox dev smoke completed, lockbox evaluation not run.

This run prepares the final SFT adapter for the frozen lockbox v1 evaluation. It trains only on the existing public sample train split and runs only a non-lockbox dev smoke check before stopping.

## Frozen Boundary

- Git commit: `3fb352b49a4dfbca891687a11703aa6521de4a55`
- Data freeze commit: `3fb352b`
- Lockbox manifest: `data/lockbox/lockbox-v1.manifest.json`
- Lockbox hash: `06114cf3ad6029930284af5f2245fb2c4a8174fd35c6a1107f4c73482b555b33`
- Lockbox run status: `not_run`
- Lockbox failure inspection: `false`

## Training Data

- Manifest: `public-sample-20260619T090925Z`
- SFT file SHA-256: `4b677420f766555c04199f15f69f41f3b3ad36ad3cd5c33d2b40b0e3f8573587`
- Train split canonical SHA-256: `2dcc97a41f8c4417160e7ee5f5dc8de6e49410ffa7d2f43828dfb99b7bdba02d`
- Split counts: train `282`, dev `207`, test `207`

Hash method: SHA-256 over ordered train rows serialized as canonical JSON with sorted keys, compact separators, UTF-8, and newline delimiters.

## Model And Training

- Base model: `Qwen/Qwen2.5-7B-Instruct`
- Base model revision: `16c174980d8a1492910551634b4969e69cdc2444`
- Prompt policy: `unified_gold_free_v1`
- Trainer: `trl.SFTTrainer`
- Seed: `7170`
- LoRA: r `16`, alpha `32`, dropout `0.05`, target modules `q_proj,k_proj,v_proj,o_proj`
- Steps: `3132`
- Epoch config: `12`
- Batch: per-device `1`, gradient accumulation `1`
- Learning rate: `0.00005`

Training result:

- Training status: `training_completed`
- Training exit code: `0`
- Observed optimizer steps: `3132`
- Adapter model SHA-256: `d7722c2c11b08a848f4c3bb46c9088a26121e231fbaf18f8fb55eab7f3becfac`
- Adapter config SHA-256: `75007a103ecbf2f61b66c3578535743b3e87f1106393edbd476632eb0e832d83`
- Adapter weights copied to git: `false`

## Decoding And Metrics

Decoding uses greedy generation, `max_new_tokens=256`, schema guard enabled, and one schema retry. No posthoc prediction repair is enabled.

Evaluator: `voice2task-eval metrics` / `strict_contract_ladder_existing`.

Required metric surface:

- `json_parse_rate`
- `strict_schema_valid_rate`
- `semantic_contract_valid_rate`
- `contract_exact_match`
- `slot_f1`
- `slot_f1_soft`
- `task_type_accuracy`
- `route_accuracy`
- `confirmation_accuracy`
- `safety_precision`
- `safety_recall`

## Output Paths

- Adapter: `<a100_project_root>/voice2task-lockbox-v1-final-sft-prep-20260626T175358Z/runs/final-sft/adapter`
- Adapter metadata: `<a100_project_root>/voice2task-lockbox-v1-final-sft-prep-20260626T175358Z/runs/final-sft/adapter_metadata.json`
- Dev smoke predictions: `<a100_project_root>/voice2task-lockbox-v1-final-sft-prep-20260626T175358Z/evidence/dev-smoke/predictions.jsonl`
- Public dev smoke metrics: `reports/public-sample/lockbox-v1-final-sft-prep/dev-smoke/metrics.json`

## Dev Smoke

- Source: first 24 rows from the public sample dev split.
- Prediction status: `private_adapter_predictions_written`
- Prediction count: `24`
- Prompt policy: `unified_gold_free_v1`
- Metrics: `reports/public-sample/lockbox-v1-final-sft-prep/dev-smoke/metrics.json`
- This is a pipeline smoke check only, not final lockbox evaluation.

## Stop Rule

After the non-lockbox dev smoke check, stop. Do not run lockbox evaluation, inspect lockbox row failures, modify lockbox rows or manifest, add training data, tune prompts against lockbox, start DPO/GRPO, or rewrite README.
