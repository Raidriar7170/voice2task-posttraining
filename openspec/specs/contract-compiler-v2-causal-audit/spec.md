# Contract Compiler V2 Causal Audit Specification

## Purpose

Define the source-linked audit contract that separates deterministic Contract Compiler mechanics from model learning, fails closed on ineligible evidence, and constrains public claims before any compiler or decoder implementation or experiment.

## Requirements

### Requirement: Inventory the observed Contract V2 transformation boundary
The system SHALL publish a deterministic, source-linked inventory of the observed V1 prediction/evaluation path and the current internal ContractCoreV2/projection boundary before describing any candidate Contract Compiler architecture.

#### Scenario: Separate observed and candidate graphs
- **WHEN** the audit renders its transformation DAG
- **THEN** it MUST publish separate observed-current and candidate-only graphs
- **AND** every observed node and edge MUST cite a repo-relative source path plus a stable symbol or artifact identity
- **AND** candidate-only behavior MUST NOT be described as implemented, runtime-loaded, evaluator-authoritative, or production-ready

#### Scenario: Inventory decoding controls accurately
- **WHEN** the audit inspects the current prediction path
- **THEN** it MUST separately record JSON-only prompting, greedy decoding, bad-word or fence suppression, post-generation parsing/schema guard, and schema retry
- **AND** it MUST classify token-level grammar/JSON-Schema constrained decoding as absent unless an actual generation-time constraint is source-verified

### Requirement: Attribute intermediate and leaf fields to separate authorities
The system SHALL audit candidate intermediate `intent`, task-specific `slots`, `risk`, and `clarification` fields plus V1 leaf fields by recording `value_origin`, `constraint_owner`, and `transform` separately.

#### Scenario: Publish leaf-level field-authority matrix
- **WHEN** the audit inventories candidate intermediates and the compiled V1 contract
- **THEN** it MUST cover task type, route, `safety.allow`, `safety.reason`, confirmation, every task-specific `slots.<key>` leaf, normalized command, language, and contract version
- **AND** every record MUST identify value origin, constraint owner, transform, source rule or symbol, downstream metric participation, and whether the value can be mutated at that stage

#### Scenario: Preserve verifier and model boundaries
- **WHEN** a verifier or semantic checker observes a field
- **THEN** the audit MUST NOT classify that observation as model-authored correctness, deterministic policy derivation, or runtime enforcement unless the corresponding code path actually performs that operation

### Requirement: Separate renderer support from canonical compatibility
The system SHALL evaluate renderer support, determinism, legacy exact compatibility, and policy self-consistency as four distinct properties, where self-consistency does not claim external semantic correctness.

#### Scenario: Interpret existing derive-display evidence
- **WHEN** the audit cites the existing 99.77% `derive_display` support rate
- **THEN** it MUST state that support means the renderer returned a value
- **AND** it MUST NOT claim that 99.77% of rendered `normalized_command` values equal legacy canonical targets

#### Scenario: Compute compatibility over a fixed source population
- **WHEN** the audit computes renderer compatibility
- **THEN** the source population MUST be exactly the 247 rows of the current formal `data/public-samples/seed_traces.jsonl`, with one seed row as one observation and no target deduplication
- **AND** SFT augmentations, DPO pairs, predictions, and lockbox rows MUST be excluded
- **AND** it MUST report parse-valid, parse-invalid, supported, unsupported, deterministic, legacy-exact, legacy-mismatch, and policy-self-consistent counts separately
- **AND** the primary ITT denominator MUST remain 247, with parse-invalid and unsupported rows counted as failures
- **AND** any supported-only result MUST be labeled secondary and display its supported denominator
- **AND** it MUST NOT alter the renderer, gold targets, public data, predictions, or historical aggregate metrics

#### Scenario: Prevent public development-set selection
- **WHEN** renderer results include current public dev/test seed rows
- **THEN** those results MUST be `DESCRIPTIVE_ONLY` and MUST NOT select, tune, or rank a candidate compiler

### Requirement: Define distinct compiler and model causal estimands
The system SHALL define separate causal estimands for deterministic compiler behavior and model-learning behavior.

#### Scenario: Define deterministic compiler estimand
- **WHEN** the audit specifies a compiler intervention and control
- **THEN** it MUST define the observation unit, eligible population, intervention, control, outcomes, full ITT denominator, and unsupported/invalid handling
- **AND** both arms MUST consume identical frozen raw core inputs and preserve model output, data, prompt, decoding, and evaluator version
- **AND** unsupported or invalid records MUST remain failures in the primary ITT result rather than disappearing into a supported-only subset
- **AND** any delta MUST be labeled a system/compiler transformation effect rather than a model-learning effect

#### Scenario: Define model-learning estimand
- **WHEN** the audit specifies evidence for a model-learning claim
- **THEN** it MUST define a preregistered evaluation family as the observation unit plus the eligible population, intervention, control, outcomes, denominator, and invalid/unsupported handling
- **AND** control and treatment MUST match data boundary, prompt, decoding, optimization budget, compiler policy, evaluator version, and eligible evaluation set
- **AND** the design MUST predeclare multiple training seeds, aggregation, uncertainty, and guardrails before execution

#### Scenario: Prevent derived-field attribution leakage
- **WHEN** a compiler fills route, safety, confirmation, language, version, normalized command, or any other deterministic field
- **THEN** mechanical gains in those fields, semantic validity, or compiled V1 exact MUST NOT be attributed to improved model parameters

### Requirement: Audit causal confounders and negative controls
The system SHALL publish an explicit matrix of confounders, invariants, negative controls, and eligibility checks for every proposed estimand.

#### Scenario: Record known current confounders
- **WHEN** the audit evaluates current evidence eligibility
- **THEN** it MUST include spent public dev/test reuse, cross-split template/provenance contamination, single-seed or unmatched training, renderer-policy mismatch, compiler-filled metrics, prompt/decoding changes, evaluator-version changes, and post-hoc selection

#### Scenario: Require invariant checks
- **WHEN** a future compiler comparison is proposed
- **THEN** it MUST require raw-core identity, row/order identity, source hash identity, prompt/decoding identity, evaluator identity, and no prediction repair as machine-checkable invariants

#### Scenario: Define negative controls
- **WHEN** the audit recommends a future causal experiment
- **THEN** it MUST include negative controls capable of detecting metric movement caused only by constants, field copying, policy defaults, or evaluation plumbing

### Requirement: Classify evidence fail closed
The system SHALL assign each audited claim exactly one status from `CAUSAL_IDENTIFICATION_SUPPORTED`, `CAUSAL_IDENTIFICATION_BLOCKED`, or `DESCRIPTIVE_ONLY`, with machine-readable reasons.

#### Scenario: Block unsupported causal claims
- **WHEN** any required intervention, control, invariant, provenance, eligible evaluation, or uncertainty condition is missing
- **THEN** the status MUST NOT be `CAUSAL_IDENTIFICATION_SUPPORTED`
- **AND** the report MUST identify the missing conditions without fabricating an effect estimate

#### Scenario: Treat current evidence conservatively
- **WHEN** the audit considers the current spent public dev/test boundary or the consumed one-look lockbox-v1
- **THEN** full compiler/model improvement identification MUST be `CAUSAL_IDENTIFICATION_BLOCKED`
- **AND** renderer/transformation mechanics MAY be `DESCRIPTIVE_ONLY` but MUST NOT be `CAUSAL_IDENTIFICATION_SUPPORTED`
- **AND** it MUST NOT reuse lockbox-v1 for renderer, prompt, schema, decoding, data, or compiler tuning

### Requirement: Enforce an explicit audit input whitelist
The system SHALL fail closed unless every audit input belongs to the declared public-safe source whitelist.

#### Scenario: Permit aggregate lockbox evidence only
- **WHEN** the audit reads lockbox-v1 evidence
- **THEN** it MAY read only the frozen manifest, final run card, base/final aggregate metrics, and final comparison
- **AND** it MUST NOT read `data/lockbox/lockbox-v1.jsonl`, drafts, row-level failures, raw/private predictions, private corpora, caches, adapters, or checkpoints

#### Scenario: Bind renderer inputs exactly
- **WHEN** the audit runs renderer compatibility analysis
- **THEN** it MUST read only the current formal seed targets and current manifest named in the audit source manifest
- **AND** any extra, missing, hash-drifted, or denylisted input MUST fail the audit without producing a causal claim

### Requirement: Publish a public-safe causal audit bundle
The system SHALL publish deterministic JSON and Markdown evidence under `reports/public-sample/contract-compiler-v2-causal-boundary/` and render the human summary from the same result.

#### Scenario: Bind public artifacts to sources
- **WHEN** the audit bundle is generated
- **THEN** it MUST record methodology version, source paths/hashes, transformation graph, field-authority matrix, decoding inventory, renderer dimensions, estimand matrices, confounders, invariants, negative controls, status reasons, execution scope, and claim flags

#### Scenario: Preserve audit-only apply boundary
- **WHEN** reports, docs, tests, or the Human Brief describe this audit-only apply
- **THEN** they MUST state `training_run=false`, `prediction_run=false`, `a100_execution=false`, `data_mutation=false`, `prompt_change=false`, `evaluator_default_change=false`, `compiler_implementation=false`, `decoder_implementation=false`, and `historical_metrics_rescored=false`
- **AND** they MUST state `lockbox_row_level_read=false`, `clean_evaluation_run=false`, and `public_dev_test_selection=false`
- **AND** they MUST NOT claim model improvement, held-out recovery, natural-ASR generalization, checkpoint/adapter release, production readiness, safety readiness, or live-browser benchmark improvement

#### Scenario: Reject private or mutable evidence
- **WHEN** audit artifacts are prepared for commit
- **THEN** validation MUST reject raw private rows, absolute local or remote paths, host/SSH details, secrets, tokens, raw logs, checkpoints, adapters, caches, and oversized generated corpora

### Requirement: Recommend but do not execute the next causal phase
The system SHALL recommend exactly one bounded next phase based on the audit status without executing it.

#### Scenario: Recommend an evidence-design phase when identification is blocked
- **WHEN** current compiler/model causal identification is blocked by spent or unmatched evidence
- **THEN** the recommendation MUST define the missing preregistration, clean evaluation, matched arms, seed/uncertainty, and invariant requirements
- **AND** it MUST NOT generate data, launch training/prediction, implement the compiler/decoder, or reuse the consumed lockbox in this audit phase
