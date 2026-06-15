## ADDED Requirements

### Requirement: Merge reviewed family-stratified candidates into the formal public sample
The system SHALL support an explicitly approved merge of reviewed
family-stratified generalization candidates into the formal public sample while
preserving public-safety validation, split labels, and claim boundaries.

#### Scenario: Merge candidate seeds with split preservation
- **WHEN** the family-stratified candidate merge command runs with the reviewed candidate seed file and current formal public seed file
- **THEN** it MUST append exactly the reviewed family-stratified candidate seed rows to `data/public-samples/seed_traces.jsonl`
- **AND** it MUST reject extra, missing, duplicate, already-merged, or unreviewed candidate rows
- **AND** each merged candidate seed MUST preserve its original `train`, `dev`, or `test` split label
- **AND** each merged candidate seed MUST use public-safe formal provenance and a schema-valid Browser Task Contract
- **AND** existing public rows MUST keep their split labels, row IDs, inputs, and target contracts

#### Scenario: Rebuild formal public sample artifacts after family merge
- **WHEN** family-stratified candidate seeds have been merged
- **THEN** `sft_public_sample.jsonl`, `dpo_public_sample.jsonl`, and `manifest_public_sample.json` MUST be regenerated from `seed_traces.jsonl`
- **AND** the manifest counts MUST match generated JSONL row counts
- **AND** the manifest MUST record that family-stratified candidates are now formal public sample rows
- **AND** existing slot-value candidate manifest metadata MUST remain present when those rows are still in the seed file

#### Scenario: Preserve family metadata through formal rebuild
- **WHEN** merged family-stratified seeds are expanded into SFT rows
- **THEN** each original and augmented SFT row MUST preserve `family_id`, `family_stratification=true`, and a source reference to the merged candidate seed
- **AND** original candidate SFT rows MAY receive DPO hard negatives through the normal public DPO builder
- **AND** augmented candidate SFT rows MUST remain SFT rows and MUST NOT receive separate DPO hard negatives

#### Scenario: Preserve merge claim boundaries
- **WHEN** reports, manifests, tests, or Human Briefs describe the family-stratified merge
- **THEN** they MUST state that the data merge and SFT/DPO rebuild do not by themselves prove held-out generalization recovery, model recovery, adapter release, checkpoint release, production readiness, private-corpus generalization, public full-corpus release, or live-browser benchmark improvement
- **AND** they MUST state that strict `contract_exact_match` remains the primary future evaluation metric
