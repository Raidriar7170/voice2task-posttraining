# Clean Matched Compiler / Model Causal Evidence Design

This is a reviewed design-only contract. It does not materialize clean evidence, freeze an executable protocol, or run either experiment.

## Exact truth surface

- evidence_status=DESIGN_ONLY
- decision=PREREGISTRATION_DESIGN_READY_EXECUTION_BLOCKED
- design_contract_status=REVIEWED_DESIGN_ONLY
- protocol_freeze_status=NOT_FROZEN
- clean_population_status=NOT_MATERIALIZED
- compiler_causal_identification=CAUSAL_IDENTIFICATION_BLOCKED
- model_learning_causal_identification=CAUSAL_IDENTIFICATION_BLOCKED
- experiment_preregistration_status=NOT_EXECUTABLE
- execution_readiness=false

## Frozen source manifest

| path | sha256 |
| --- | --- |
| `reports/public-sample/contract-compiler-v2-causal-boundary/summary.json` | `5bfcbedfb6130207c577f6b03608a555086ac33f1295d4a7f225917be0cde1c1` |
| `openspec/specs/contract-compiler-v2-causal-audit/spec.md` | `5db529a5e603b610e79a4ba1e2b3765ba6fa6c263de48b2df629b69863e7e26c` |
| `CONTEXT.md` | `becc5b54eaf66f90789b77fb4fef1a6fc14bd62ae8ef50f9f26a0791edd4b993` |
| `data/public-samples/manifest_public_sample.json` | `f866c173795e97953b1dec85611b405867d0a29497910282f99d399f109cda95` |
| `reports/public-sample/split-integrity-audit/summary.json` | `ac10bd0a1c3fefb717433de68ae29d049069b521bae8599234b7f52faec8f598` |
| `data/lockbox/lockbox-v1.manifest.json` | `72471bac59749f3bc9d21d73db47dafe1f160b978f5ac3971434e13527ddedde` |
| `reports/lockbox-v1/final-evaluation/run-card.json` | `39e59cd6e16baa7adadb6b3c474e7fce8bfe8223e5980a1288a1c50432acec66` |
| `reports/lockbox-v1/final-evaluation/base/metrics.json` | `400fa753e6e8bde611af4e4f9623155ceff6664454bfea0f57748043243cd02f` |
| `reports/lockbox-v1/final-evaluation/final-sft/metrics.json` | `aaecc8dcdad90e70c0f8a7c59a21d2e65d8d42bae3e304e4dce9b049390bc829` |
| `reports/lockbox-v1/final-evaluation/comparison.json` | `48fae0e85e016c1872477881939716076d96998d0c63f83adf1e9be42d9ed544` |

## Canonical execution bindings

29 / 29 execution bindings remain `UNBOUND_BY_DESIGN`.

| field | value |
| --- | --- |
| `acquisition_source` | `UNBOUND_BY_DESIGN` |
| `acquisition_frame_version` | `UNBOUND_BY_DESIGN` |
| `semantic_family_key` | `UNBOUND_BY_DESIGN` |
| `partition_algorithm` | `UNBOUND_BY_DESIGN` |
| `partition_seed` | `UNBOUND_BY_DESIGN` |
| `strata_definition` | `UNBOUND_BY_DESIGN` |
| `target_total_family_count` | `UNBOUND_BY_DESIGN` |
| `target_partition_allocation` | `UNBOUND_BY_DESIGN` |
| `minimum_families_per_partition` | `UNBOUND_BY_DESIGN` |
| `compiler_control` | `UNBOUND_BY_DESIGN` |
| `compiler_intervention` | `UNBOUND_BY_DESIGN` |
| `model_control` | `UNBOUND_BY_DESIGN` |
| `model_training_intervention` | `UNBOUND_BY_DESIGN` |
| `paired_model_seed_list` | `UNBOUND_BY_DESIGN` |
| `compiler_effect_scale` | `UNBOUND_BY_DESIGN` |
| `model_effect_scale` | `UNBOUND_BY_DESIGN` |
| `compiler_mde_or_sensitivity_target` | `UNBOUND_BY_DESIGN` |
| `model_mde_or_sensitivity_target` | `UNBOUND_BY_DESIGN` |
| `compiler_target_power_or_beta` | `UNBOUND_BY_DESIGN` |
| `model_target_power_or_beta` | `UNBOUND_BY_DESIGN` |
| `alpha` | `UNBOUND_BY_DESIGN` |
| `compiler_family_variance_or_icc_assumption` | `UNBOUND_BY_DESIGN` |
| `model_family_variance_or_icc_assumption` | `UNBOUND_BY_DESIGN` |
| `paired_seed_correlation_assumption` | `UNBOUND_BY_DESIGN` |
| `seed_failure_or_attrition_assumption` | `UNBOUND_BY_DESIGN` |
| `compiler_interval_and_multiplicity_method` | `UNBOUND_BY_DESIGN` |
| `model_interval_and_multiplicity_method` | `UNBOUND_BY_DESIGN` |
| `guardrail_margins` | `UNBOUND_BY_DESIGN` |
| `stop_rules` | `UNBOUND_BY_DESIGN` |

## Future clean acquisition and partition contract

- Acquisition plans: 1 (status: `NOT_STARTED`).
- `compiler_system_evaluation`: materialization `NOT_MATERIALIZED`, sealing `NOT_SEALED`, one-look `NOT_AVAILABLE`.
- `model_learning_evaluation`: materialization `NOT_MATERIALIZED`, sealing `NOT_SEALED`, one-look `NOT_AVAILABLE`.
- Family assignment happens exactly once in a future materialization from frozen mechanics, before row authoring, annotation, gold access, or outcome access.
- No clean row, family registry, membership, gold label, or prediction was created.

## Separate preregistration cards

### Compiler / system (`compiler_system_evaluation`)

- Full fixed-population ITT; invalid, unsupported, compiler-error, and missing records remain primary failures.
- Paired within-record contrasts aggregate within semantic family; row-independent intervals are forbidden.
- Any future identified effect is labeled `system_compiler_transformation_effect` only.

### Model learning (`model_learning_evaluation`)

- Exactly one future training intervention, matched arms, and at least three all-assigned paired seeds are required.
- Failed or missing assigned seeds receive preregistered failure codes and remain in the seed-level ITT denominator.
- Compiler-filled outcomes cannot identify model learning.

## Power and uncertainty

- Compiler dependence: paired_record, semantic_family_cluster.
- Model dependence: semantic_family_cluster, paired_seed.
- MDE, target power/beta, alpha, ICC/family variance, paired-seed correlation, seed attrition, interval/multiplicity methods, guardrail margins, and stop rules remain pre-outcome `UNBOUND_BY_DESIGN` bindings.

## Readiness lifecycle

0. `DESIGN_ONLY` — reached=true
1. `EXPERIMENT_BINDINGS_COMPLETE` — reached=false
2. `PROTOCOL_FROZEN` — reached=false
3. `POPULATION_MATERIALIZED_AND_SEALED` — reached=false
4. `ARM_ARTIFACTS_FROZEN` — reached=false
5. `ELIGIBLE_FOR_ONE_LOOK` — reached=false

## Next phase

- `materialize-and-freeze-clean-compiler-model-evaluation-boundary-v1`
- executed=false
- A separate review is required; that phase may not run compiler or model experiments.
