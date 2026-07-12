## Why

The repository now has repaired evaluator and split-integrity truth surfaces, but it still lacks a causal contract for judging a proposed Contract Compiler V2. Without that audit, deterministic field completion, renderer coverage, prompt/decoding changes, and model learning could be conflated into one apparent metric gain even though current public dev/test are spent and lockbox-v1 is already consumed one-look evidence.

## What Changes

- Audit the actual current V1 model-output path, internal ContractCoreV2 projection, deterministic envelope, renderer, semantic validator, retry, and decoding boundaries from code and committed artifacts.
- Publish a field-authority and transformation DAG that covers candidate intermediate `intent`, task-specific `slots`, `risk`, and `clarification` plus V1 leaf fields, and records `value_origin`, `constraint_owner`, and `transform` separately.
- Distinguish JSON-only prompting, greedy decoding, bad-word suppression, post-generation schema guard, and retry from genuine token-level JSON/grammar constrained decoding.
- Measure renderer support separately from legacy canonical compatibility. In particular, the existing 99.77% `derive_display` support rate MUST NOT be interpreted as `normalized_command` exact compatibility.
- Define causal estimands with observation unit, eligible population, outcome, denominator, unsupported/invalid handling, ITT versus supported-only reporting, intervention/control arms, matched-run invariants, confounders, negative controls, acceptance criteria, and the evidence required before any compiler-related improvement claim.
- Classify the current evidence as `CAUSAL_IDENTIFICATION_SUPPORTED`, `CAUSAL_IDENTIFICATION_BLOCKED`, or `DESCRIPTIVE_ONLY`, with fail-closed public claims and a bounded next-step recommendation.
- Produce deterministic public-safe JSON/Markdown audit evidence and a concise Chinese Human Brief in a later audit-only apply.
- Non-goals: no Contract Compiler implementation, token-level decoder implementation, V1 schema/default evaluator change, public data resplit, new lockbox, prompt change, training, prediction, A100 execution, DPO/GRPO, generic chat fine-tuning, skill routing, GUI action policy learning, full private-corpus release, checkpoint/adapter release, production-readiness claim, or live-browser benchmark claim.

## Capabilities

### New Capabilities

- `contract-compiler-v2-causal-audit`: define the field-authority, transformation, causal-identification, evidence-classification, and public-claim requirements for auditing Contract Compiler V2 before implementation or experimentation.

### Modified Capabilities

None. This audit consumes the existing `internal-contract-core-v2`, `contract-evaluation`, `voice2task-dataset-preparation`, and `supervised-contract-tuning` truth surfaces without changing their runtime behavior.

## Impact

- Read-only analysis of evaluator, training/prediction, ContractCoreV2, projection, schema/semantic validation, and public evidence code paths.
- A deterministic audit helper plus focused tests may be added during audit-only apply solely to derive public-safe audit artifacts from an explicit source whitelist.
- New report artifacts under `reports/public-sample/contract-compiler-v2-causal-boundary/`, a Human Brief, and evidence-index/current-status navigation updates.
- This opening creates only proposal/design/spec/tasks. A later apply remains audit-only: no model, dataset, prompt, prediction, evaluator default, compiler runtime, or historical metric may change.
