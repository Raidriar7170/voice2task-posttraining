# Clean Evaluation Acquisition and Binding Review Checklist

This is preparation-only operator guidance. It is not an execution input and records no human acceptance.

- Independence: source provider must differ from source reviewer.
- Independence: lockbox validator must differ from lockbox reviewer.
- Ancestry exclusions: public train/dev/test, remediation, challenge, prediction, and lockbox-v1 row content.
- Every proposed binding requires derivation evidence, applicability, and a zero-access attestation.
- Compiler and model power assumptions require independent statistical review.
- Human acceptance is a separate future gate and is not recorded by this pack.
- The operator alone may manually copy a completed envelope to `data/local-private/clean-compiler-model-evaluation-boundary-v1/review-inputs/`.
- The tool never creates or modifies this root.

## Responsibility matrix (33 rows; no preapproval)

| row_id | scope | name | envelope section | provider | independent reviewer | required evidence | applicability | zero-access attestation | human acceptance gate | preapproval status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| component:binding_packet | component | binding_packet | binding_draft | NOT_SUPPLIED | NOT_SUPPLIED | NOT_SUPPLIED | NOT_SUPPLIED | NOT_SUPPLIED | NOT_RECORDED | NOT_RECORDED |
| component:source_contract | component | source_contract | source_contract_draft | NOT_SUPPLIED | NOT_SUPPLIED | NOT_SUPPLIED | NOT_SUPPLIED | NOT_SUPPLIED | NOT_RECORDED | NOT_RECORDED |
| component:compiler_card | component | compiler_card | compiler_card_draft | NOT_SUPPLIED | NOT_SUPPLIED | NOT_SUPPLIED | NOT_SUPPLIED | NOT_SUPPLIED | NOT_RECORDED | NOT_RECORDED |
| component:model_card | component | model_card | model_card_draft | NOT_SUPPLIED | NOT_SUPPLIED | NOT_SUPPLIED | NOT_SUPPLIED | NOT_SUPPLIED | NOT_RECORDED | NOT_RECORDED |
| binding:acquisition_source | binding | acquisition_source | binding_draft | NOT_SUPPLIED | NOT_SUPPLIED | NOT_SUPPLIED | NOT_SUPPLIED | NOT_SUPPLIED | NOT_RECORDED | NOT_RECORDED |
| binding:acquisition_frame_version | binding | acquisition_frame_version | binding_draft | NOT_SUPPLIED | NOT_SUPPLIED | NOT_SUPPLIED | NOT_SUPPLIED | NOT_SUPPLIED | NOT_RECORDED | NOT_RECORDED |
| binding:semantic_family_key | binding | semantic_family_key | binding_draft | NOT_SUPPLIED | NOT_SUPPLIED | NOT_SUPPLIED | NOT_SUPPLIED | NOT_SUPPLIED | NOT_RECORDED | NOT_RECORDED |
| binding:partition_algorithm | binding | partition_algorithm | binding_draft | NOT_SUPPLIED | NOT_SUPPLIED | NOT_SUPPLIED | NOT_SUPPLIED | NOT_SUPPLIED | NOT_RECORDED | NOT_RECORDED |
| binding:partition_seed | binding | partition_seed | binding_draft | NOT_SUPPLIED | NOT_SUPPLIED | NOT_SUPPLIED | NOT_SUPPLIED | NOT_SUPPLIED | NOT_RECORDED | NOT_RECORDED |
| binding:strata_definition | binding | strata_definition | binding_draft | NOT_SUPPLIED | NOT_SUPPLIED | NOT_SUPPLIED | NOT_SUPPLIED | NOT_SUPPLIED | NOT_RECORDED | NOT_RECORDED |
| binding:target_total_family_count | binding | target_total_family_count | binding_draft | NOT_SUPPLIED | NOT_SUPPLIED | NOT_SUPPLIED | NOT_SUPPLIED | NOT_SUPPLIED | NOT_RECORDED | NOT_RECORDED |
| binding:target_partition_allocation | binding | target_partition_allocation | binding_draft | NOT_SUPPLIED | NOT_SUPPLIED | NOT_SUPPLIED | NOT_SUPPLIED | NOT_SUPPLIED | NOT_RECORDED | NOT_RECORDED |
| binding:minimum_families_per_partition | binding | minimum_families_per_partition | binding_draft | NOT_SUPPLIED | NOT_SUPPLIED | NOT_SUPPLIED | NOT_SUPPLIED | NOT_SUPPLIED | NOT_RECORDED | NOT_RECORDED |
| binding:compiler_control | binding | compiler_control | binding_draft | NOT_SUPPLIED | NOT_SUPPLIED | NOT_SUPPLIED | NOT_SUPPLIED | NOT_SUPPLIED | NOT_RECORDED | NOT_RECORDED |
| binding:compiler_intervention | binding | compiler_intervention | binding_draft | NOT_SUPPLIED | NOT_SUPPLIED | NOT_SUPPLIED | NOT_SUPPLIED | NOT_SUPPLIED | NOT_RECORDED | NOT_RECORDED |
| binding:model_control | binding | model_control | binding_draft | NOT_SUPPLIED | NOT_SUPPLIED | NOT_SUPPLIED | NOT_SUPPLIED | NOT_SUPPLIED | NOT_RECORDED | NOT_RECORDED |
| binding:model_training_intervention | binding | model_training_intervention | binding_draft | NOT_SUPPLIED | NOT_SUPPLIED | NOT_SUPPLIED | NOT_SUPPLIED | NOT_SUPPLIED | NOT_RECORDED | NOT_RECORDED |
| binding:paired_model_seed_list | binding | paired_model_seed_list | binding_draft | NOT_SUPPLIED | NOT_SUPPLIED | NOT_SUPPLIED | NOT_SUPPLIED | NOT_SUPPLIED | NOT_RECORDED | NOT_RECORDED |
| binding:compiler_effect_scale | binding | compiler_effect_scale | binding_draft | NOT_SUPPLIED | NOT_SUPPLIED | NOT_SUPPLIED | NOT_SUPPLIED | NOT_SUPPLIED | NOT_RECORDED | NOT_RECORDED |
| binding:model_effect_scale | binding | model_effect_scale | binding_draft | NOT_SUPPLIED | NOT_SUPPLIED | NOT_SUPPLIED | NOT_SUPPLIED | NOT_SUPPLIED | NOT_RECORDED | NOT_RECORDED |
| binding:compiler_mde_or_sensitivity_target | binding | compiler_mde_or_sensitivity_target | binding_draft | NOT_SUPPLIED | NOT_SUPPLIED | NOT_SUPPLIED | NOT_SUPPLIED | NOT_SUPPLIED | NOT_RECORDED | NOT_RECORDED |
| binding:model_mde_or_sensitivity_target | binding | model_mde_or_sensitivity_target | binding_draft | NOT_SUPPLIED | NOT_SUPPLIED | NOT_SUPPLIED | NOT_SUPPLIED | NOT_SUPPLIED | NOT_RECORDED | NOT_RECORDED |
| binding:compiler_target_power_or_beta | binding | compiler_target_power_or_beta | binding_draft | NOT_SUPPLIED | NOT_SUPPLIED | NOT_SUPPLIED | NOT_SUPPLIED | NOT_SUPPLIED | NOT_RECORDED | NOT_RECORDED |
| binding:model_target_power_or_beta | binding | model_target_power_or_beta | binding_draft | NOT_SUPPLIED | NOT_SUPPLIED | NOT_SUPPLIED | NOT_SUPPLIED | NOT_SUPPLIED | NOT_RECORDED | NOT_RECORDED |
| binding:alpha | binding | alpha | binding_draft | NOT_SUPPLIED | NOT_SUPPLIED | NOT_SUPPLIED | NOT_SUPPLIED | NOT_SUPPLIED | NOT_RECORDED | NOT_RECORDED |
| binding:compiler_family_variance_or_icc_assumption | binding | compiler_family_variance_or_icc_assumption | binding_draft | NOT_SUPPLIED | NOT_SUPPLIED | NOT_SUPPLIED | NOT_SUPPLIED | NOT_SUPPLIED | NOT_RECORDED | NOT_RECORDED |
| binding:model_family_variance_or_icc_assumption | binding | model_family_variance_or_icc_assumption | binding_draft | NOT_SUPPLIED | NOT_SUPPLIED | NOT_SUPPLIED | NOT_SUPPLIED | NOT_SUPPLIED | NOT_RECORDED | NOT_RECORDED |
| binding:paired_seed_correlation_assumption | binding | paired_seed_correlation_assumption | binding_draft | NOT_SUPPLIED | NOT_SUPPLIED | NOT_SUPPLIED | NOT_SUPPLIED | NOT_SUPPLIED | NOT_RECORDED | NOT_RECORDED |
| binding:seed_failure_or_attrition_assumption | binding | seed_failure_or_attrition_assumption | binding_draft | NOT_SUPPLIED | NOT_SUPPLIED | NOT_SUPPLIED | NOT_SUPPLIED | NOT_SUPPLIED | NOT_RECORDED | NOT_RECORDED |
| binding:compiler_interval_and_multiplicity_method | binding | compiler_interval_and_multiplicity_method | binding_draft | NOT_SUPPLIED | NOT_SUPPLIED | NOT_SUPPLIED | NOT_SUPPLIED | NOT_SUPPLIED | NOT_RECORDED | NOT_RECORDED |
| binding:model_interval_and_multiplicity_method | binding | model_interval_and_multiplicity_method | binding_draft | NOT_SUPPLIED | NOT_SUPPLIED | NOT_SUPPLIED | NOT_SUPPLIED | NOT_SUPPLIED | NOT_RECORDED | NOT_RECORDED |
| binding:guardrail_margins | binding | guardrail_margins | binding_draft | NOT_SUPPLIED | NOT_SUPPLIED | NOT_SUPPLIED | NOT_SUPPLIED | NOT_SUPPLIED | NOT_RECORDED | NOT_RECORDED |
| binding:stop_rules | binding | stop_rules | binding_draft | NOT_SUPPLIED | NOT_SUPPLIED | NOT_SUPPLIED | NOT_SUPPLIED | NOT_SUPPLIED | NOT_RECORDED | NOT_RECORDED |
