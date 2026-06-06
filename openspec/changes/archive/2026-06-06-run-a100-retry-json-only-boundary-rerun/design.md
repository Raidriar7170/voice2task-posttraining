## Context

The previous A100 stop-boundary rerun recorded strict final `json_valid_rate=0.0` and `contract_exact_match=0.0`: raw attempts remained JSON objects missing `task_type`, and retry attempts remained prose/Markdown-wrapped JSON fragments. The local `tighten-retry-json-only-output-boundary` phase strengthened the retry prompt and metadata visibility but explicitly made no A100 or model-quality claim.

This phase is the smallest private-runtime follow-up: run the existing private adapter once in prediction-only mode, keep strict evaluation unchanged, and publish only sanitized public-sample evidence.

## Goals / Non-Goals

**Goals:**

- Execute a bounded A100 prediction-only train-split rerun with `schema_retry_enabled=true`, `schema_repair_applied=false`, `overfit_diagnostic=true`, and `generalization_claim=false`.
- Observe whether retry attempts still produce prose/Markdown-wrapped fragments or become strict whole JSON objects.
- Preserve generated model evidence, including invalid outputs.
- Publish public-safe metrics, schema guard summary, retry-boundary diagnosis, manifest, report, and Human Brief.

**Non-Goals:**

- No model training, checkpoint release, adapter release, public full-corpus release, parser relaxation, evaluator metric change, prediction repair, prediction re-score, semantic-equivalence scoring, slot normalization, production-readiness claim, held-out generalization claim, model-quality claim, or live-browser benchmark claim.

## Decisions

1. Use prediction-only A100 execution after local prompt hardening.
   - Rationale: local prompt visibility does not prove private adapter behavior; a real prediction export is needed.
   - Alternative considered: infer success from local prompt tests. Rejected because the model may still wrap retry outputs.

2. Compare only against bounded public-safe prior artifacts.
   - Rationale: the relevant baseline is the previous A100 stop-boundary rerun plus the local retry-boundary hardening pack.
   - Alternative considered: compare to unrelated older A100 phases. Rejected to avoid cherry-picking and overclaim risk.

3. Keep strict parsing and strict metrics unchanged.
   - Rationale: success should come from model output becoming a whole valid JSON object, not from extracting fragments or relaxing evaluator semantics.
   - Alternative considered: parse embedded JSON from wrapped retry text. Rejected as prediction repair/parser relaxation.

## Risks / Trade-offs

- A100 rerun may still produce wrapped retry fragments -> Mitigation: publish the failure honestly and recommend a narrower next prompt/decoding diagnosis.
- Private runtime safety -> Mitigation: check GPU/process occupancy, use one selected GPU with `CUDA_VISIBLE_DEVICES`, keep all remote-created files under the AGENTS-defined approved A100 root, and copy back only sanitized evidence.
- Overclaim risk -> Mitigation: reports and Human Brief must state train-split diagnostic only and no model-quality/generalization claim.
