## Context

The previous A100 retry JSON-only rerun showed `json_valid_rate=0.0`, `contract_exact_match=0.0`, and retry attempts still wrapped as prose/Markdown fragments. The immediately preceding local phase changed the retry prompt construction so the retry attempt is rendered through a machine-only chat-template/fallback boundary and exposed in metadata/prompt snapshots.

This phase asks only one question: with the same bounded train split and existing private adapter, does the new retry template boundary change observed strict output behavior? It must remain prediction-only and public-safe.

## Goals / Non-Goals

**Goals:**

- Run one A100 prediction-only train-split rerun with `schema_retry_enabled=true` and the current machine-only retry template boundary.
- Use an approved private A100 output root represented in committed artifacts only as `<a100_project_root>`.
- Inspect GPU occupancy before launch, select an idle GPU, and set `CUDA_VISIBLE_DEVICES` explicitly.
- Publish sanitized public artifacts that preserve raw/retry model evidence, strict metrics, retry wrapper status, schema guard status, prompt snapshot retry-template metadata, generation trace, and leak-scan results.
- Compare against `reports/public-sample/a100-retry-json-only-boundary-rerun/` and `reports/public-sample/retry-template-decoding-boundary/`.

**Non-Goals:**

- No training, fine-tuning, DPO, checkpoint release, adapter release, parser relaxation, evaluator metric change, prediction repair, prediction re-score, semantic-equivalence scoring, slot normalization, generic chat fine-tuning, skill routing, GUI action policy learning, first-phase GRPO, production-readiness claim, held-out generalization claim, public full-corpus release, live-browser benchmark claim, or model-quality claim.
- No committed private override, raw log, private host detail, private path, SSH detail, token, secret, checkpoint, adapter, cache, or private corpus row.

## Execution Plan

1. Add local tests that fail until the rerun evidence pack records retry-template boundary metadata, strict non-claim boundaries, source links, and post-archive leak scans.
2. Prepare the A100 runtime in an approved private project directory, using the current committed repo state and a repo-external private prediction override.
3. Before launching GPU work, run GPU/process occupancy inspection and choose an idle GPU only when safe.
4. Launch the prediction-only rerun with one explicit GPU, train split rows, the existing private adapter, strict parser semantics, and no training.
5. Copy only sanitized public artifacts into `reports/public-sample/a100-retry-template-boundary-rerun/`.
6. Generate rerun diagnosis/manifest/report/Human Brief locally from sanitized artifacts.
7. Run leak scans, focused tests, full validation, Reviewer pass, archive, post-archive/final leak scans, and guarded auto integration.

## Risks / Trade-offs

- The retry template boundary may still not improve strict metrics. Mitigation: report the observed result plainly and keep invalid outputs invalid.
- A100 GPUs may be occupied or private adapter/runtime paths may be unavailable. Mitigation: stop as blocked rather than using an unsafe GPU or committing private details.
- Sanitization could miss private paths in copied sidecars. Mitigation: use existing public display placeholders, run leak scans over evidence/brief/archive/specs, and keep private logs/configs outside git.
