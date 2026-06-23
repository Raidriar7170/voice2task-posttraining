# Copy-Shadow Template-Disjoint Challenge

This document records the bounded `evaluate-frozen-copy-shadow-policy-on-template-disjoint-challenge-set` phase.

## Status

Decision: `CHALLENGE_EVALUATION_BLOCKED`.

The challenge rows and audits were frozen, and hook hardening was implemented. Observed adapter-backed challenge inference did not run because no local identity-verifiable frozen adapter was loadable.

Authoritative artifacts:

- Challenge rows: [`../data/public-samples/copy-shadow-template-disjoint-challenge-v1.jsonl`](../data/public-samples/copy-shadow-template-disjoint-challenge-v1.jsonl)
- Summary: [`../reports/public-sample/copy-shadow-template-disjoint-challenge-v1/challenge-summary.json`](../reports/public-sample/copy-shadow-template-disjoint-challenge-v1/challenge-summary.json)
- Blocked evidence: [`../reports/public-sample/copy-shadow-template-disjoint-challenge-v1/blocked.json`](../reports/public-sample/copy-shadow-template-disjoint-challenge-v1/blocked.json)
- Template audit: [`../reports/public-sample/copy-shadow-template-disjoint-challenge-v1/template-disjoint-audit.json`](../reports/public-sample/copy-shadow-template-disjoint-challenge-v1/template-disjoint-audit.json)

## Challenge Purpose

The challenge evaluates whether frozen observe-only copy-backed provenance evidence can generalize beyond templates used for scope selection, policy design, verifier design, model training, and dev/test debugging.

This phase does not train, repair predictions, change policy scopes, change prompts, change decoding, change evaluators, change schemas, enable runtime enforcement, enable action provenance, or trust normalized provenance.

## Template-Disjoint Definition

Accepted rows must have no overlap with current train/dev/test rows by:

- sample id;
- exact input text;
- canonical template signature;
- slot-value-stripped template signature.

Near-duplicate thresholds are deterministic: accepted rows stay below character 3-gram Jaccard `0.80` and normalized edit similarity `0.85`. The v1 audit accepted all 120 rows with 0 overlap counts.

## Freeze Flow

1. Load and validate frozen `copy-backed-scope-policy-v1`.
2. Materialize deterministic public-safe rows.
3. Validate each `gold_contract` as BrowserTaskContract V1.
4. Verify gold feasibility against the frozen policy expectation.
5. Write the challenge JSONL and report bundle.
6. Attempt local frozen adapter identity discovery.
7. If no adapter is loadable and identity-verifiable, write `CHALLENGE_EVALUATION_BLOCKED` and stop.

## Scope Coverage

The frozen v1 challenge has 120 rows:

- `search:search_web:query`: 30 rows.
- `form_fill:fill_form:field`: 30 rows.
- `extract:extract_page:target`: 30 rows.
- `blocked:deny:action`: 30 disabled negative-control rows.

Condition tags cover exact unique, duplicate exact, source absent, multiple entity distractor, partial span trap, normalization candidate, normalization collision, long input, ASR-style noise, synthetic PII, out-of-scope action, and invalid/unparseable output fault injection.

## Prediction Boundary

Observed challenge prediction may only use the canonical `voice2task-train sft-predict` entrypoint or library-equivalent `voice2task.training.run_sft_prediction_export`.

No standalone verifier script may be used as the primary online-sidecar result. In this blocked run, adapter-backed prediction was not attempted because local adapter configs only exposed unresolved `<a100_project_root>` paths or otherwise lacked identity-verifiable loadable adapters.

## Provenance And Correctness Split

Online sidecars remain gold-free and privacy-preserving. They may record hashes, policy metadata, hook status, write status, and slot diagnostics.

Gold correctness belongs only in offline challenge audits after prediction and sidecar artifacts are frozen. Because observed inference was blocked, trusted/gold-correct rates are not reported for this phase.

## Trust Rules

- Exact unique copy-backed provenance is the only trusted path.
- Normalized matches are candidate-only and never trusted.
- Action provenance remains disabled.
- Source spans must pass full offset/hash/back-slice validation.
- Sidecar path conflicts are isolated and never fallback-written.

## Privacy Defaults

Sidecars default to hash-and-offset-only retention. `retain_input_text=true`, `retain_raw_model_output=true`, and `fail_isolated=false` are rejected as invalid shadow config.

The challenge rows are public-safe synthetic text. Synthetic PII tags are labels for test coverage, not real personal data.

## Decision Gate

The only possible validation label for a successful observed challenge is still observe-only. Runtime enforcement cannot be recommended in this phase.

This run selected `CHALLENGE_EVALUATION_BLOCKED` because no frozen adapter identity was verifiable locally. It does not prove frozen-policy generalization and does not lower any safety or production-readiness boundary.
