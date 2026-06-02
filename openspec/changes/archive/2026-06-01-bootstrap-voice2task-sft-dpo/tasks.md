## 1. Project Scaffolding

- [x] 1.1 Create Python project metadata, package layout, CLI entrypoints, and gitignore rules for generated corpora, checkpoints, logs, and local reports.
- [x] 1.2 Add dependency groups for dataset/evaluation, SFT/DPO training, development tests, and optional engineering training.
- [x] 1.3 Add README quickstart that states first-phase scope, public/private data boundaries, non-goals, and no released-checkpoint claim.
- [x] 1.4 Add public-safe directory conventions for `data/public-samples/`, generated local corpora, `configs/`, `reports/`, and exported adapter metadata.

## 2. Dataset Preparation

- [x] 2.1 Define the browser task contract schema and dataset row schemas for SFT rows, DPO pairs, manifests, and rejection categories.
- [x] 2.2 Implement the dataset builder for public-sample mode from sanitized seed fixtures.
- [x] 2.3 Implement local/private corpus building from a configured Voice-to-Browser Agent seed trace path.
- [x] 2.4 Implement schema-preserving augmentation hooks that keep target contracts and safety labels stable.
- [x] 2.5 Implement hard-negative generation with route, safety, confirmation, slot, underspecified, and malformed-schema rejection categories.
- [x] 2.6 Add dataset validation tests and a command such as `voice2task-data validate` for row schema, split, DPO pair, and public-artifact policy checks.

## 3. Supervised Contract Tuning

- [x] 3.1 Add Qwen-family SFT LoRA config templates for small local/dev runs and larger A100 runs.
- [x] 3.2 Implement SFT message formatting so assistant targets are canonical browser task contract JSON.
- [x] 3.3 Implement the TRL/PEFT SFT training script with dataset manifest tracking, checkpoint output, and adapter metadata export.
- [x] 3.4 Implement rule and prompt-only baseline evaluation paths for comparison with SFT outputs.
- [x] 3.5 Add smoke tests for SFT formatting, config parsing, dry-run data loading, and adapter metadata generation.

## 4. Preference Contract Tuning

- [x] 4.1 Implement DPO pair validation for same-input chosen/rejected pairs and required rejection reasons.
- [x] 4.2 Implement DPO dataset formatting for chosen/rejected browser task contract outputs.
- [x] 4.3 Implement the TRL/PEFT DPO training script with SFT/base model references, manifest tracking, checkpoint output, and adapter metadata export.
- [x] 4.4 Add DPO slice reporting for route, safety, confirmation, slot, schema, and underspecified failures.
- [x] 4.5 Add tests for DPO pair validation, weak-pair rejection, and DPO formatting.

## 5. Contract Evaluation

- [x] 5.1 Implement the evaluator for JSON valid rate, task type accuracy, route accuracy, safety precision/recall, confirmation accuracy, slot F1, and contract exact-match checks.
- [x] 5.2 Implement failure-slice summaries with sanitized example identifiers.
- [x] 5.3 Implement optional controlled execution smoke against a configured Voice-to-Browser Agent validation target.
- [x] 5.4 Implement machine-readable metrics JSON and human-readable Markdown report generation.
- [x] 5.5 Add tests for schema metrics, route/safety/confirmation metrics, slot F1, failure slices, and execution-smoke disabled/enabled behavior.

## 6. Reports, Briefs, and Public Safety

- [x] 6.1 Add baseline-vs-SFT-vs-DPO report templates with honest claim boundaries and no live-browser improvement claim unless supported by evidence.
- [x] 6.2 Add a concise Chinese Human Brief HTML under `docs/human-briefs/` summarizing the phase, key artifacts, verification, and remaining risks.
- [x] 6.3 Add public-leak scan tooling for absolute local paths, secrets/tokens, private IPs, raw private rows, and oversized generated corpora.
- [x] 6.4 Add release/readiness checklist for public sample data, manifests, reports, adapter metadata, and validation commands.

## 7. Fresh Validation

- [x] 7.1 Run formatting/lint/type checks for the Python project.
- [x] 7.2 Run unit tests for schema, dataset, SFT formatting, DPO pairs, evaluator metrics, reports, and leak scans.
- [x] 7.3 Run public-sample dataset build and validation commands from a clean checkout.
- [x] 7.4 Run schema metrics and DPO pair checks on sample fixtures.
- [x] 7.5 Run public-leak scan against committed artifacts and generated public reports.
- [x] 7.6 Run `openspec validate --all --strict` and `git diff --check`.
