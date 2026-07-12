## Context

The archived Contract Compiler V2 causal audit fixed three constraints for any next experiment: current public dev/test are `DEVELOPMENT_ONLY_SPENT`, lockbox-v1 is consumed one-look aggregate evidence, and the current 247-seed renderer result is descriptive mechanism evidence rather than causal performance evidence. Compiler/system and model-learning effects remain separately `CAUSAL_IDENTIFICATION_BLOCKED`.

The user selected design option A: one future clean acquisition and lineage plan whose family-level partition mechanics are frozen before acquisition. Actual membership is assigned from the materialized family registry before row authoring, gold access, or outcome access, producing two family-disjoint sealed evaluation partitions. The compiler partition may be opened first without spending the model-learning partition. This change designs the contract only; it neither materializes the population nor freezes an executable experiment.

## Goals / Non-Goals

**Goals:**

- Define a future clean acquisition, lineage, family grouping, partitioning, sealing, and one-look protocol without creating or inspecting rows.
- Preserve independent evidence for compiler/system and model-learning estimands through two family-disjoint sealed partitions and two separate preregistration cards.
- Define machine-readable binding requirements, invariants, negative controls, sample-size/MDE methodology, family/seed-level uncertainty, hard stops, and claim boundaries.
- Produce a deterministic public-safe design bundle whose truthful terminal state is design-ready but execution-blocked.
- Recommend one bounded materialization-and-freeze phase without executing it.

**Non-Goals:**

- No clean-row creation, collection, selection, annotation, gold access, outcome access, deduplication, resplit, or sample-size adaptation after outcomes.
- No compiler, renderer, decoder, prompt, schema, evaluator-default, verifier-enforcement, or runtime implementation.
- No training, prediction, A100 job, DPO/GRPO, checkpoint/adapter release, model selection, or experiment execution.
- No lockbox-v1 raw-row read, reuse, tuning, row-level overlap analysis, or second look.
- No generic chat fine-tuning, skill routing, GUI action policy learning, public full-corpus release, natural-ASR claim, model-improvement claim, executable-quality claim, production/safety readiness claim, or live-browser benchmark claim.

## Decisions

### 1. Use one acquisition plan with two family-disjoint sealed partitions

The future population design contains `compiler_system_evaluation` and `model_learning_evaluation` partitions. The partition algorithm, seed, family key, strata, target allocation, and minimum-size rule must be bound and frozen before acquisition starts. At materialization, the source-hashed acquisition frame produces a family registry; actual family membership is then assigned exactly once by the frozen mechanics and sealed before row authoring, annotation, gold access, or outcome access. A semantic family may appear in only one partition, and neither partition may contribute rows or families to training, development, remediation, challenge construction, or the other partition.

Opening the compiler partition consumes only its own one-look state. The model partition remains sealed until a separately reviewed model-learning protocol reaches its future execution gate. A shared sequential partition was rejected because inspecting compiler outcomes would spend the model evidence. Two independent acquisitions were rejected because they duplicate lineage and annotation cost and exceed the smallest useful next phase.

### 2. Treat cleanliness as a lineage and blinding claim, not a creation timestamp

The future acquisition plan must exclude ancestry from current public train/dev/test, remediation and challenge artifacts, existing predictions, and lockbox-v1. It must predeclare exact, normalized, template, semantic-family, and provenance disjointness checks. Any future lockbox overlap check may expose only a sealed aggregate attestation from an authorized validator; this design and its later apply cannot read lockbox rows.

This change has one canonical execution-binding inventory. Every field below is exactly `UNBOUND_BY_DESIGN` in this phase and blocks `EXPERIMENT_BINDINGS_COMPLETE` until a later reviewed phase gives it a concrete value and source hash:

- acquisition: `acquisition_source`, `acquisition_frame_version`;
- partition: `semantic_family_key`, `partition_algorithm`, `partition_seed`, `strata_definition`, `target_total_family_count`, `target_partition_allocation`, `minimum_families_per_partition`;
- arms and seeds: `compiler_control`, `compiler_intervention`, `model_control`, `model_training_intervention`, `paired_model_seed_list`;
- power and analysis: `compiler_effect_scale`, `model_effect_scale`, `compiler_mde_or_sensitivity_target`, `model_mde_or_sensitivity_target`, `compiler_target_power_or_beta`, `model_target_power_or_beta`, `alpha`, `compiler_family_variance_or_icc_assumption`, `model_family_variance_or_icc_assumption`, `paired_seed_correlation_assumption`, `seed_failure_or_attrition_assumption`, `compiler_interval_and_multiplicity_method`, `model_interval_and_multiplicity_method`, `guardrail_margins`, and `stop_rules`.

Actual realized family counts and partition membership are not execution bindings that can be invented in this design. They are future materialization evidence produced from the frozen acquisition frame and mechanics before any row, gold, or outcome access. The later materialization proposal must bind the canonical inventory from a pre-outcome power/sensitivity analysis and source-provenance review, freeze the protocol, and only then materialize and seal membership.

### 3. Keep compiler/system and model-learning cards independent

The compiler card uses one frozen raw record as the observation unit. Both arms consume byte-identical model output, semantic core, legacy envelope metadata, row order, prompt/decoding provenance, and evaluator version. The control preserves the legacy envelope; the intervention is a named future candidate compiler. Primary analysis is full-population ITT compiled-V1 strict exact, with invalid and unsupported records retained as failures. Supported-only results are secondary diagnostics. Each record forms a paired within-record contrast; record contrasts are aggregated within semantic family before a family-clustered paired interval or randomization method is applied. Row-independent intervals are forbidden, and multiplicity across primary, guardrail, and negative-control outcomes must be bound before outcomes. Safety, confirmation, slots, executable gates, constants, copying, policy defaults, and evaluation plumbing are predeclared guardrails or negative controls. Any future effect is labeled only `system_compiler_transformation_effect`.

The model card uses one preregistered evaluation family as the observation unit and requires exactly one named training intervention. If the intervention is not bound, or if prompt, output schema, decoder, compiler policy, evaluator, data boundary, optimization budget, seed list, or eligible evaluation population differ across arms, model-learning identification remains blocked. Compiler-filled fields cannot be primary model outcomes.

### 4. Predeclare paired seeds and hierarchical uncertainty

The model card requires at least three paired seeds, a frozen all-assigned seed list, and a seed-level ITT failure policy. Every assigned seed remains in the primary denominator; a missing, failed, or invalid arm result receives its predeclared failure code and cannot be deleted, replaced, or selectively rerun. The aggregation order is fixed as family-level aggregation within each assigned seed followed by paired aggregation across the same assigned seed list, with failure-coded seeds retained. Uncertainty must respect both semantic-family clustering and seed pairing; ordinary row-level confidence intervals that treat rows or repeated seeds as independent are forbidden.

Compiler and model sample-size/MDE contracts must separately bind effect scale, MDE or sensitivity target, target power or beta, alpha, family-level variance or ICC assumptions, interval method, multiplicity policy, guardrail margins, and stop rules. The model contract must additionally bind paired-seed correlation and seed failure/attrition assumptions. Family aggregation, seed aggregation, and all failure coding must be fixed before clean outcomes are accessible. Historical public aggregate evidence may inform sensitivity assumptions but cannot select or resize the clean population after outcomes.

### 5. Use a fail-closed readiness state machine

The future protocol lifecycle is:

```text
DESIGN_ONLY
→ EXPERIMENT_BINDINGS_COMPLETE
→ PROTOCOL_FROZEN
→ POPULATION_MATERIALIZED_AND_SEALED
→ ARM_ARTIFACTS_FROZEN
→ ELIGIBLE_FOR_ONE_LOOK
```

This change may reach only `DESIGN_ONLY`. Its terminal truth surface is:

```text
evidence_status=DESIGN_ONLY
decision=PREREGISTRATION_DESIGN_READY_EXECUTION_BLOCKED
design_contract_status=REVIEWED_DESIGN_ONLY
protocol_freeze_status=NOT_FROZEN
clean_population_status=NOT_MATERIALIZED
compiler_causal_identification=CAUSAL_IDENTIFICATION_BLOCKED
model_learning_causal_identification=CAUSAL_IDENTIFICATION_BLOCKED
experiment_preregistration_status=NOT_EXECUTABLE
execution_readiness=false
```

Missing bindings, lineage ambiguity, partition-family overlap, hash drift, early outcome access, arm mismatch, seed loss, prediction repair, unsupported-case filtering, or one-look reuse must stop advancement and emit machine-readable reasons.

### 6. Publish a deterministic public-safe design bundle

A later apply may add a read-only helper and focused tests that consume only an explicit source whitelist: the archived causal audit summary, its main capability spec, current `CONTEXT.md`, the public manifest and split-integrity summary, and aggregate lockbox status artifacts expressly allowed by the archived audit. The helper must deny raw lockbox rows, drafts, row failures, raw/private predictions, private corpora, caches, adapters, checkpoints, logs, and local/remote secrets.

Every whitelisted source must resolve strictly to a regular file inside the repository root, without symlink or alternate-logical-path redirection. Path validation and exact whitelist membership happen before filesystem reads. Hashing, UTF-8 decoding, and source-anchor validation use the same single bytes snapshot so a source cannot change between separate hash and anchor reads.

The apply output is deterministic `summary.json` and `summary.md` under `reports/public-sample/clean-matched-causal-evidence-design/`, plus a Chinese Human Brief and evidence navigation. It records the acquisition/partition schema, both cards, bound/unbound fields, state machine, invariants, negative controls, uncertainty contract, source hashes, false execution flags, status reasons, and exactly one unexecuted next-phase recommendation.

### 7. Recommend materialization before any compiler or model pilot

If the design passes review, its only next recommendation is `materialize-and-freeze-clean-compiler-model-evaluation-boundary-v1`. That later phase may acquire, validate, partition, and seal the population under a separately reviewed OpenSpec change. It still may not implement or run the compiler/model experiments. A compiler matched pilot may be considered only after the compiler partition is sealed; model training may be considered only after its independent protocol and partition remain sealed.

### 8. Separate live context from historical audit replay

The archived causal audit used logical source `CONTEXT.md` at SHA-256 `2ffc67d81be8b3e482555efd23db5b0bf60239eb4ef4d9e24514cae24ea1009f`. This apply advances live `CONTEXT.md` to record the current design-only truth, so historical replay must resolve that one declared logical source to a byte-exact, content-addressed phase-time snapshot. The archived audit source manifest, logical path/hash, JSON/Markdown bytes, status, and metrics remain unchanged.

The resolver is audit-only and exact: no multi-hash allowlist, fallback to live context, glob, or broad discovery is allowed. The new clean-matched design helper continues to read and freeze the current live `CONTEXT.md`; historical and current lineage therefore remain explicit and independent.

## Risks / Trade-offs

- [Two partitions reduce the families available to each estimand] → Require pre-outcome family-level MDE/power planning and block materialization if either partition cannot meet the declared sensitivity floor.
- [A design template may be misrepresented as a frozen preregistration] → Publish `protocol_freeze_status=NOT_FROZEN`, `experiment_preregistration_status=NOT_EXECUTABLE`, and `execution_readiness=false` everywhere.
- [A semantic-core versus full-V1 comparison may change prompt, schema, and compiler together] → Require exactly one bound model intervention and label any bundled pipeline comparison as non-identifying.
- [Rows within a family or runs sharing a seed may be treated as independent] → Require family/seed hierarchical aggregation and reject row-only uncertainty.
- [Failed seeds or unsupported rows may be dropped] → Retain them under predeclared failure rules in the primary denominator.
- [A newly authored or synthetic set may be called natural ASR] → Require source-provenance labels and forbid natural-ASR claims unless independently established.
- [Checking lockbox overlap could create a second look] → Permit only a future sealed aggregate attestation; never expose raw lockbox rows to this design path.
- [A mutable live context can break historical audit replay] → Resolve the archived audit's declared phase-time context through one content-addressed snapshot while keeping archived report bytes unchanged.
- [A whitelisted lexical path can redirect through a symlink or change between hash and anchor reads] → Require strict in-repo regular-file resolution and one bytes snapshot per source.

## Migration Plan

1. Add RED tests for the design schema, two sealed partitions, separate cards, tri-state bindings, state machine, uncertainty contract, whitelist/denylist, strict source resolution, statuses, and false execution flags.
2. Implement a deterministic read-only design helper, add content-addressed historical-context replay for the archived audit, and generate public-safe JSON/Markdown evidence without creating rows or executing experiments or rewriting archived reports.
3. Review the clean lineage contract, partition independence, both preregistration cards, uncertainty, invariants, negative controls, and next-phase boundary.
4. Update evidence navigation and generate the Chinese Human Brief.
5. Run focused/full validation, public leak scan, protected-hash checks, independent reviews, and archive.

No runtime migration is required. Rollback removes only the design helper/tests/reports/docs and OpenSpec artifacts; no data, prediction, model, or historical metric can require restoration.

## Open Questions

There are no hidden execution assumptions. Every field in the canonical execution-binding inventory in Decision 2 is intentionally `UNBOUND_BY_DESIGN`; each blocks `EXPERIMENT_BINDINGS_COMPLETE` and protocol freeze until a later reviewed phase binds it before acquisition. Actual realized family counts and membership remain future materialization evidence and cannot be inferred from this design.
