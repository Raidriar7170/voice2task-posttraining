# voice2task-dataset-preparation Specification

## Purpose
Define how Voice2Task builds speech-to-contract datasets from sanitized seed traces while keeping committed public samples separate from generated local/private corpora.
## Requirements
### Requirement: Build public sample and local private corpora
The system SHALL build speech-to-contract datasets from sanitized Voice-to-Browser Agent seed artifacts while separating committed public samples from generated local/private corpora.

#### Scenario: Build public sample dataset
- **WHEN** a developer runs the dataset builder in public-sample mode
- **THEN** the system writes a small sanitized JSONL sample that contains spoken command or ASR transcript inputs, target browser task contracts, split labels, and provenance metadata safe for git

#### Scenario: Build local private corpus
- **WHEN** a developer runs the dataset builder with a local seed trace corpus path
- **THEN** the system writes generated train/dev/test JSONL files under a gitignored local artifact directory and emits a manifest with counts, split names, and source summaries

### Requirement: Preserve schema and safety labels during augmentation
The system SHALL support schema-preserving augmentation that changes Chinese phrasing without changing the target browser task contract or safety label.

#### Scenario: Augment a seed example
- **WHEN** the builder expands a seed example into paraphrased Chinese commands
- **THEN** every augmented row retains the original target contract, route decision, safety decision, and confirmation expectation unless an explicit hard-negative row is being generated

### Requirement: Generate hard negative pairs
The system SHALL generate DPO-ready hard negative pairs where rejected contracts are plausible but wrong, unsafe, underspecified, or routed incorrectly.

#### Scenario: Generate DPO pairs
- **WHEN** the builder creates preference data
- **THEN** each pair contains the same input, one chosen browser task contract, one rejected browser task contract, and a rejection reason category

### Requirement: Validate dataset rows
The system SHALL validate every generated dataset row against the browser task contract schema and public/private artifact policy.

#### Scenario: Reject invalid dataset rows
- **WHEN** a row has malformed JSON, a missing required field, an invalid split label, or forbidden local path content in a public artifact
- **THEN** the builder fails validation and reports the row identifier and failure category

### Requirement: Define normalized-command canonical target policy
The system SHALL treat `normalized_command` in gold Browser Task Contract targets as a stable canonical intent phrase, not a verbatim transcript and not an evaluator-side semantic-equivalence label.

#### Scenario: Preserve canonical target across paraphrases
- **WHEN** schema-preserving augmentations rephrase the same source command
- **THEN** every augmented row MUST retain the original target contract, including the same canonical `normalized_command`, route, safety decision, confirmation expectation, and slots unless an explicit hard-negative row is being generated

#### Scenario: Canonicalize first-phase public sample target phrases
- **WHEN** public-sample seed targets define `normalized_command`
- **THEN** search targets MUST prefer a concise `搜索...` intent phrase, navigation targets MUST use a concise open-site intent phrase, form-fill targets MUST use a concise fill-and-confirm phrase when confirmation is required, and unsafe payment denial targets MUST use a concise refusal intent phrase

#### Scenario: Bound canonical target interpretation
- **WHEN** documentation, manifests, tests, or Human Briefs describe normalized-command canonicalization
- **THEN** they MUST state that canonical target policy does not change evaluator exact-match behavior, does not normalize predictions, does not mark strings equivalent, and does not re-score prior evidence

### Requirement: Keep public search targets aligned to canonical query slots
The public sample dataset SHALL encode public-readonly search/weather task targets with compact `slots.query` strings that align with the canonical `normalized_command` query phrase.

#### Scenario: Build public sample search rows
- **WHEN** the public sample dataset is generated or inspected
- **THEN** the search/weather seed row and its schema-preserving augmentations MUST use `slots={"query":"北京明天天气"}`
- **AND** the same rows MUST use `normalized_command="搜索北京明天天气"`
- **AND** they MUST NOT use `slots.city`, `slots.date`, or artificial token-spaced query strings such as `北京 明天 天气`

#### Scenario: Build public sample DPO pairs
- **WHEN** DPO pairs are generated or inspected for the public search/weather seed row
- **THEN** chosen contracts MUST preserve the compact `slots.query` target
- **AND** wrong-slot hard negatives MAY alter the query value but MUST NOT introduce `city/date` as an accepted target shape

### Requirement: Use current compact public search train targets for A100 rerun
The A100 search query slot-policy rerun SHALL use the current public sample train rows and SHALL preserve their compact public-readonly search targets in copied gold evidence.

#### Scenario: Copy train split gold rows
- **WHEN** `train_split_gold.jsonl` is generated for the rerun evidence pack
- **THEN** the three public search/weather train rows MUST use `slots={"query":"北京明天天气"}` and `normalized_command="搜索北京明天天气"`
- **AND** they MUST NOT contain `slots.city`, `slots.date`, `slots.topic`, or the artificial token-spaced query string `北京 明天 天气`

### Requirement: Generate decomposed search-slot hard negatives
The public sample DPO builder SHALL reject decomposed public-readonly search/weather slot shapes while preserving compact `slots.query` chosen targets.

#### Scenario: Build decomposed slot hard negative
- **WHEN** DPO pairs are generated for a public-readonly search/weather seed row whose chosen contract uses compact `slots.query`
- **THEN** the builder MUST include a rejected contract whose `slots` object uses decomposed `city`, `date`, and `topic` keys instead of `query`
- **AND** the rejected contract MUST use a distinct rejection reason that is counted in the manifest and DPO summary
- **AND** the chosen contract MUST retain compact `slots.query` and `normalized_command`

#### Scenario: Limit decomposed slot negative scope
- **WHEN** DPO pairs are generated for non-search contracts or search contracts without compact public-readonly `slots.query`
- **THEN** the builder MUST NOT invent `city/date/topic` rejected slots for those rows

### Requirement: Keep public sample artifacts synchronized after seed expansion
The system SHALL regenerate public sample SFT, DPO, and manifest artifacts whenever committed public seed traces change.

#### Scenario: Regenerate derived public sample artifacts
- **WHEN** `data/public-samples/seed_traces.jsonl` is expanded or edited
- **THEN** `sft_public_sample.jsonl`, `dpo_public_sample.jsonl`, and `manifest_public_sample.json` MUST be regenerated from the same seed file
- **AND** the manifest counts MUST match the generated SFT and DPO JSONL row counts
- **AND** the generated artifacts MUST remain public-safe

### Requirement: Encode public extract-price targets canonically
The public sample dataset SHALL encode current-page price extraction requests with a canonical extract-page contract target instead of search fallback or generic query slots.

#### Scenario: Build public extract-price rows
- **WHEN** the public sample dataset is generated or inspected for the current extract-price seed and its schema-preserving augmentations
- **THEN** those rows MUST use `task_type="extract"` and `route="extract_page"`
- **AND** they MUST use `safety.allow=true`, `safety.reason="public_readonly"`, and `confirmation_required=false`
- **AND** they MUST use `slots={"target":"商品价格"}` and `normalized_command="提取页面商品价格"`
- **AND** they MUST NOT encode the target as `slots.query`, `slots.page_url`, or a public web search route

### Requirement: Generate extract-price hard negatives
The public sample DPO builder SHALL generate extract-specific hard negatives that reject search fallback and query/page-url slot shapes for current-page price extraction targets.

#### Scenario: Build extract search-fallback hard negative
- **WHEN** DPO pairs are generated for a public-safe `extract`/`extract_page` row whose chosen contract uses `slots.target`
- **THEN** the builder MUST include a rejected contract with a distinct rejection reason for extract search fallback
- **AND** the rejected contract MUST change the output toward a plausible but wrong `search`/`search_web` contract
- **AND** the chosen contract MUST retain `task_type="extract"`, `route="extract_page"`, `slots.target`, and the canonical normalized command

#### Scenario: Build extract query-slot hard negative
- **WHEN** DPO pairs are generated for a public-safe `extract`/`extract_page` row whose chosen contract uses `slots.target`
- **THEN** the builder MUST include a rejected contract with a distinct rejection reason for query-slot extraction drift
- **AND** the rejected contract MUST replace the accepted `slots.target` shape with a wrong query/page-url style slot shape
- **AND** the chosen contract MUST retain `slots.target` and the canonical normalized command

#### Scenario: Limit extract hard-negative scope
- **WHEN** DPO pairs are generated for non-extract contracts or extract contracts without a public-safe target slot
- **THEN** the builder MUST NOT invent extract-price search-fallback or query-slot rejected contracts for those rows

### Requirement: Generate extract-price canonical wording hard negatives
The public sample DPO builder SHALL generate extract-price canonical wording hard negatives that reject strict-wrong target synonyms while preserving the canonical accepted contract.

#### Scenario: Build generic price wording negative
- **WHEN** DPO pairs are generated for a public-safe `extract`/`extract_page` row whose accepted contract uses `slots.target="商品价格"` and `normalized_command="提取页面商品价格"`
- **THEN** the builder MUST include a rejected contract whose rejection reason identifies generic price target wording
- **AND** the rejected contract MUST use a plausible but strict-wrong target such as `slots.target="价格"` or `normalized_command="页面价格"`
- **AND** the chosen contract MUST retain `slots.target="商品价格"` and `normalized_command="提取页面商品价格"`

#### Scenario: Build listed-price wording negative
- **WHEN** DPO pairs are generated for a public-safe `extract`/`extract_page` row whose accepted contract uses the canonical商品价格 target
- **THEN** the builder MUST include a rejected contract whose rejection reason identifies listed-price wording drift
- **AND** the rejected contract MUST use a plausible but strict-wrong target such as `slots.target="标价"` or `normalized_command="提取页面标价"`
- **AND** the chosen contract MUST retain the canonical accepted contract

#### Scenario: Build extra-particle normalized-command negative
- **WHEN** DPO pairs are generated for a public-safe `extract`/`extract_page` row whose accepted contract uses the canonical商品价格 target
- **THEN** the builder MUST include a rejected contract whose rejection reason identifies extra-particle extract wording
- **AND** the rejected contract MUST preserve task, route, safety, confirmation, and `slots.target` while changing `normalized_command` to a strict-wrong wording such as `提取页面上的商品价格`

#### Scenario: Limit canonical wording negatives
- **WHEN** DPO pairs are generated for non-extract contracts, non-public rows, or extract rows whose accepted target is not canonical商品价格
- **THEN** the builder MUST NOT invent extract-price canonical wording hard negatives for those rows

### Requirement: Keep extract-price public targets canonical after wording repair
The public sample dataset SHALL keep the original extract-price seed and schema-preserving augmentations aligned to the same canonical accepted contract.

#### Scenario: Inspect extract-price public rows after regeneration
- **WHEN** public sample SFT artifacts are regenerated for the canonical wording phase
- **THEN** all extract-price public rows MUST use `task_type="extract"`, `route="extract_page"`, `slots={"target":"商品价格"}`, and `normalized_command="提取页面商品价格"`
- **AND** they MUST NOT use accepted targets such as `价格`, `标价`, `页面价格`, or `提取页面上的商品价格`

### Requirement: Add train-only public held-out repair exemplars
The system SHALL add public-safe train split seed traces that cover the same contract families as the failed public held-out residuals without moving existing public `dev` or `test` rows into train.

#### Scenario: Build train repair rows
- **WHEN** the public sample dataset is generated after the repair seed expansion
- **THEN** it MUST include train split SFT rows for navigate/open-url, ambiguous clarify, confirmation-required form fill, and unsafe payment blocking
- **AND** those train rows MUST use distinct public-safe inputs and target values from the existing public held-out `dev` and `test` rows
- **AND** existing public `dev` and `test` rows MUST retain their split labels and target contracts

#### Scenario: Preserve repair target contracts
- **WHEN** schema-preserving augmentations are generated for the repair train seeds
- **THEN** each augmentation MUST preserve the original target contract, including task type, route, safety reason, confirmation expectation, slots, and canonical normalized command

### Requirement: Generate held-out residual repair hard negatives
The public sample DPO builder SHALL generate task-family-specific hard negatives for the public held-out residual families.

#### Scenario: Build clarify action-drift negative
- **WHEN** DPO pairs are generated for a public-safe clarify contract with `safety.reason="ambiguous_request"`
- **THEN** the builder MUST include a rejected contract that drifts to a concrete action such as search or navigate
- **AND** the chosen contract MUST retain `task_type="clarify"`, `route="clarify"`, `confirmation_required=true`, and an `ambiguity` slot

#### Scenario: Build blocked payment action-drift negative
- **WHEN** DPO pairs are generated for a public-safe unsafe payment block contract
- **THEN** the builder MUST include a rejected contract that allows or routes the request as a concrete search or navigation action
- **AND** the chosen contract MUST retain `task_type="blocked"`, `route="deny"`, `safety.allow=false`, `safety.reason="unsafe_payment"`, `confirmation_required=true`, and a payment-control reason slot

#### Scenario: Build form confirmation drift negative
- **WHEN** DPO pairs are generated for a public-safe confirmation-required form-fill contract
- **THEN** the builder MUST include a rejected contract that drops confirmation, changes the confirmation safety reason, or changes the accepted `slots.field` shape
- **AND** the chosen contract MUST retain `task_type="form_fill"`, `route="fill_form"`, `safety.reason="requires_confirmation"`, `confirmation_required=true`, and `slots.field`

#### Scenario: Build navigate canonical URL drift negative
- **WHEN** DPO pairs are generated for a public-safe navigation contract with a canonical URL slot and open-site normalized command
- **THEN** the builder MUST include a rejected contract with a strict-wrong URL or normalized-command variant
- **AND** the chosen contract MUST retain the canonical URL slot and canonical navigation normalized command

#### Scenario: Limit held-out residual negatives
- **WHEN** DPO pairs are generated for rows outside the matching public-safe task family
- **THEN** the builder MUST NOT invent held-out residual repair negatives for unrelated rows

### Requirement: Diagnose public-sample family coverage before scaling data
The system SHALL support a local public-sample coverage diagnosis that informs
whether the next data step should be targeted family coverage instead of broad
data scaling.

#### Scenario: Compare train coverage with held-out families
- **WHEN** the public sample contains train, dev, and test rows
- **THEN** the diagnosis MUST summarize coverage by source family, task type, route, safety reason, confirmation behavior, and slot keys for each split
- **AND** it MUST identify held-out families that appear in train at dataset level but were absent from the actual tiny-adapter training subset

#### Scenario: Preserve data-generation boundary
- **WHEN** coverage gaps are reported
- **THEN** the diagnosis MUST NOT create new public rows, mutate seed traces, mutate SFT/DPO rows, or change the public manifest

### Requirement: Design slot value generalization cases before materialization
The system SHALL publish a public-safe case-design artifact for targeted slot value generalization before modifying public sample seeds, generating rows, or launching training.

#### Scenario: Cover residual buckets
- **WHEN** targeted slot value residual diagnosis evidence is available
- **THEN** the case design MUST propose candidate case groups for `slot_value_language_variant`, `slot_value_canonical_phrase_drift`, and `normalized_command_paraphrase_drift`
- **AND** each candidate group MUST identify the residual source family, affected field path, canonical gold value, observed wrong value pattern, and intended training or validation purpose

#### Scenario: Keep design separate from data mutation
- **WHEN** the case design artifact is generated
- **THEN** it MUST state `new_data_generated=false`, `public_sample_modified=false`, and `training_run=false`
- **AND** it MUST require a later approved OpenSpec change before candidate cases are materialized into `seed_traces.jsonl`, rebuilt datasets, or training configs

#### Scenario: Preserve held-out and exact-match boundaries
- **WHEN** the case design recommends a next phase
- **THEN** it MUST preserve strict `contract_exact_match` as the primary metric
- **AND** it MUST NOT relax evaluator rules, normalize predictions, re-score prior evidence, promote semantic equivalence, or claim held-out recovery

### Requirement: Materialize reviewed slot value generalization candidates separately
The system SHALL materialize reviewed slot value generalization case groups into a public-safe candidate dataset that remains separate from the formal public sample until a later approved change merges it.

#### Scenario: Generate candidate seeds from reviewed design
- **WHEN** the slot value generalization case-design artifact contains the reviewed case groups
- **THEN** the materializer MUST write exactly one public-safe candidate seed row for each reviewed case group
- **AND** each candidate seed MUST use a schema-valid Browser Task Contract with canonical slot values or normalized command wording from the design
- **AND** each candidate seed MUST include provenance linking back to the source case group and design artifact

#### Scenario: Keep formal public sample unchanged
- **WHEN** candidate materialization runs
- **THEN** it MUST NOT edit `data/public-samples/seed_traces.jsonl`, `sft_public_sample.jsonl`, `dpo_public_sample.jsonl`, or `manifest_public_sample.json`
- **AND** the materialization manifest MUST state `public_sample_modified=false`, `training_run=false`, `prediction_run=false`, and `dpo_run=false`

#### Scenario: Expand candidate SFT rows without DPO
- **WHEN** candidate seeds contain schema-preserving augmentations
- **THEN** the materializer MUST expand them into candidate SFT rows using the existing SFT row schema and augmentation provenance
- **AND** it MUST NOT generate DPO pairs or hard negatives in this phase

#### Scenario: Preserve evaluation and claim boundaries
- **WHEN** materialized candidate artifacts, reports, or Human Briefs describe the phase
- **THEN** they MUST state that strict `contract_exact_match` remains the primary metric
- **AND** they MUST NOT claim held-out generalization recovery, model recovery, checkpoint release, adapter release, production readiness, private-corpus generalization, or live-browser benchmark improvement

### Requirement: Materialize family-stratified generalization candidates separately
The system SHALL materialize a public-safe family-stratified generalization
candidate dataset that remains separate from the formal public sample until a
later approved change explicitly merges it.

#### Scenario: Generate family-stratified candidate seeds
- **WHEN** the family-stratified materializer runs
- **THEN** it MUST write public-safe candidate seed rows for the text/ASR-to-contract families `search`, `navigation`, `clarify`, `form_fill`, `extract`, `blocked_payment`, and `confirmation`
- **AND** each family MUST contain `train`, `dev`, and `test` seed rows
- **AND** each candidate seed MUST include provenance with `source_mode="family_stratified_generalization_candidate_seed"`, `public_safe=true`, `candidate_status="standalone_not_formal_public_sample"`, `family_id`, `split_role`, and `family_stratification=true`

#### Scenario: Preserve split separation
- **WHEN** candidate seeds are generated
- **THEN** source IDs MUST be unique and MUST NOT appear in more than one split
- **AND** each family-specific slot signature MUST be disjoint across `train`, `dev`, and `test`
- **AND** the materialization manifest MUST record per-family per-split seed and SFT counts

#### Scenario: Expand candidate SFT rows without DPO
- **WHEN** candidate seeds contain schema-preserving augmentations
- **THEN** the materializer MUST expand them into candidate SFT rows using the existing SFT row schema and augmentation provenance
- **AND** it MUST NOT generate DPO pairs or hard negatives in this phase

#### Scenario: Keep formal public sample unchanged
- **WHEN** family-stratified candidate materialization runs
- **THEN** it MUST NOT edit `data/public-samples/seed_traces.jsonl`, `sft_public_sample.jsonl`, `dpo_public_sample.jsonl`, or `manifest_public_sample.json`
- **AND** the materialization manifest MUST state `formal_public_sample_modified=false`, `training_run=false`, `prediction_run=false`, `dpo_run=false`, `a100_execution=false`, and `evaluator_metric_change=false`

#### Scenario: Preserve evaluation and claim boundaries
- **WHEN** family-stratified candidate artifacts, reports, or Human Briefs describe the phase
- **THEN** they MUST state that strict `contract_exact_match` remains the primary metric
- **AND** they MUST NOT claim held-out generalization recovery, model recovery, checkpoint release, adapter release, production readiness, private-corpus generalization, public full-corpus release, or live-browser benchmark improvement

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

### Requirement: Merge reviewed slot value candidates into the formal public sample
The system SHALL support an explicitly approved merge of reviewed slot value
generalization candidates into the formal public sample while preserving
public-safety validation and held-out split boundaries.

#### Scenario: Merge candidate seeds as train rows
- **WHEN** the candidate merge command is run with the reviewed candidate seed
  file and current formal public seed file
- **THEN** it MUST append exactly the reviewed slot value candidate seed rows to
  `data/public-samples/seed_traces.jsonl`
- **AND** it MUST reject extra, missing, duplicate, or unreviewed candidate rows
- **AND** each merged candidate seed MUST use `split="train"`, public-safe
  provenance, and a schema-valid Browser Task Contract
- **AND** existing public `dev` and `test` rows MUST keep their split labels,
  row IDs, inputs, and target contracts

#### Scenario: Rebuild formal public sample artifacts
- **WHEN** candidate seeds have been merged
- **THEN** `sft_public_sample.jsonl`, `dpo_public_sample.jsonl`, and
  `manifest_public_sample.json` MUST be regenerated from `seed_traces.jsonl`
- **AND** the manifest counts MUST match generated JSONL row counts
- **AND** the manifest MUST record that slot value candidates are now formal
  public sample rows

#### Scenario: Generate hard negatives for merged candidates
- **WHEN** DPO pairs are generated for merged candidate original rows
- **THEN** each original candidate row MUST receive the standard
  `wrong_task_type` hard negative
- **AND** eligible candidate families MUST receive the relevant residual drift
  hard negatives through the normal public DPO builder
- **AND** augmented candidate rows MUST remain SFT rows and MUST NOT receive
  separate DPO hard negatives

#### Scenario: Preserve merge claim boundaries
- **WHEN** reports, manifests, tests, or Human Briefs describe the merge
- **THEN** they MUST state that data merge and SFT/DPO rebuild do not by
  themselves prove held-out recovery, model recovery, adapter release,
  checkpoint release, production readiness, private-corpus generalization, or
  live-browser benchmark improvement

### Requirement: Materialize form-fill remediation candidates separately

The system SHALL materialize reviewed `form_fill` remediation case groups into a public-safe candidate dataset that remains separate from the formal public sample until a later approved change merges or trains on it.

#### Scenario: Generate candidate seeds from reviewed form-fill design

- **WHEN** the form-fill remediation case-design artifact contains the reviewed case groups
- **THEN** the materializer MUST write public-safe candidate seed rows for the reviewed `form_fill` cases
- **AND** each candidate seed MUST use a schema-valid Browser Task Contract with the reviewed `slots.field` value
- **AND** each candidate seed MUST include provenance linking back to the source case group, case ID, residual bucket, and design artifact

#### Scenario: Preserve form-fill canonical confirmation policy

- **WHEN** a reviewed `form_fill` remediation case is materialized
- **THEN** its target contract MUST use `task_type="form_fill"`, `route="fill_form"`, `safety.reason="requires_confirmation"`, and `confirmation_required=true`
- **AND** its canonical `normalized_command` MUST use concise `填写...并确认` wording
- **AND** the materialization evidence MUST preserve the source expected normalized-command pattern for auditability

#### Scenario: Keep formal public sample unchanged

- **WHEN** form-fill remediation candidate materialization runs
- **THEN** it MUST NOT edit `data/public-samples/seed_traces.jsonl`, `sft_public_sample.jsonl`, `dpo_public_sample.jsonl`, or `manifest_public_sample.json`
- **AND** the materialization manifest MUST state `public_sample_modified=false`, `training_run=false`, `prediction_run=false`, `dpo_run=false`, `a100_execution=false`, and `evaluator_metric_change=false`

#### Scenario: Expand candidate SFT rows without DPO

- **WHEN** candidate seeds are materialized
- **THEN** the materializer MUST expand them into candidate SFT rows using the existing SFT row schema and original-row provenance
- **AND** it MUST NOT generate DPO pairs, hard negatives, schema-preserving augmentations, or training configs in this phase

#### Scenario: Preserve evaluation and claim boundaries

- **WHEN** materialized candidate artifacts, reports, or Human Briefs describe the phase
- **THEN** they MUST state that strict `contract_exact_match` remains the primary metric
- **AND** they MUST NOT claim held-out generalization recovery, model recovery, checkpoint release, adapter release, production readiness, private-corpus generalization, public full-corpus release, or live-browser benchmark improvement

### Requirement: Preview-check form-fill remediation candidate integration

The system SHALL support a local preview integration check for standalone `form_fill` remediation candidate seeds before any later formal public-sample merge, training probe, or A100 execution.

#### Scenario: Build preview artifacts without mutating the formal public sample

- **WHEN** the integration check runs with the current formal public seed file and the reviewed `form_fill` remediation candidate seed file
- **THEN** it MUST write preview seed, SFT, DPO, and manifest artifacts under a reports directory
- **AND** it MUST NOT edit `data/public-samples/seed_traces.jsonl`, `sft_public_sample.jsonl`, `dpo_public_sample.jsonl`, or `manifest_public_sample.json`
- **AND** the evidence manifest MUST state `formal_public_sample_modified=false`

#### Scenario: Validate reviewed candidate rows before preview build

- **WHEN** the integration check reads the candidate seed file
- **THEN** it MUST reject missing, extra, duplicate, already-formal, or non-standalone candidate rows
- **AND** it MUST reject candidate IDs that already exist in the formal public seed file
- **AND** every accepted candidate MUST remain public-safe, train split, and schema-valid

#### Scenario: Record preview counts and candidate contributions

- **WHEN** the preview public-sample build succeeds
- **THEN** the evidence MUST record the current formal public counts, preview public counts, candidate seed count, candidate SFT count, candidate preview DPO count, and preview validation status
- **AND** the preview DPO count MUST be marked as preview-only, not a formal DPO rebuild

#### Scenario: Preserve execution and claim boundaries

- **WHEN** integration check artifacts, reports, or Human Briefs describe the phase
- **THEN** they MUST state that strict `contract_exact_match` remains the primary metric
- **AND** they MUST NOT claim held-out generalization recovery, model recovery, checkpoint release, adapter release, production readiness, private-corpus generalization, public full-corpus release, or live-browser benchmark improvement
- **AND** they MUST state `training_run=false`, `prediction_run=false`, `a100_execution=false`, and `evaluator_metric_change=false`

### Requirement: Merge reviewed form-fill remediation candidates into formal public sample
The system SHALL support a formal public-sample merge for the reviewed train-only `form_fill` remediation candidate seeds after preview integration has passed.

#### Scenario: Rebuild formal public sample with form-fill candidates
- **WHEN** the merge command is run with the reviewed form-fill remediation candidate seed file and the current formal public seed file
- **THEN** the system MUST append exactly 9 formalized candidate seed rows
- **AND** it MUST rebuild formal seed, SFT, DPO, and manifest artifacts in place
- **AND** the rebuilt formal public sample MUST contain 86 seed rows, 240 SFT rows, and 742 DPO pairs
- **AND** the rebuilt SFT split counts MUST be `train=102`, `dev=69`, and `test=69`

#### Scenario: Preserve candidate provenance
- **WHEN** form-fill remediation candidates are promoted into the formal public sample
- **THEN** each promoted seed MUST preserve `public_safe=true`
- **AND** each promoted seed MUST set `candidate_status=formal_public_sample`
- **AND** each promoted seed MUST identify the source candidate seed artifact
- **AND** the formal manifest MUST summarize form-fill remediation candidate counts and affected source case groups

#### Scenario: Reject unsafe or duplicate merge inputs
- **WHEN** candidate seed rows are missing, extra, duplicated, unreviewed, not train split, not standalone, not public-safe, or already present in the formal seed
- **THEN** the merge MUST fail before rewriting formal public sample artifacts

### Requirement: Record form-fill remediation merge evidence without model-quality claims
The system SHALL record public-safe evidence for the formal form-fill remediation candidate merge while preserving evaluation and execution boundaries.

#### Scenario: Write merge evidence artifacts
- **WHEN** the form-fill remediation candidate merge completes
- **THEN** the system MUST write JSON, Markdown, and manifest evidence under `reports/public-sample/form-fill-remediation-public-sample-merge/`
- **AND** the evidence MUST record formal counts, split counts, candidate source, candidate seed rows, candidate SFT rows, candidate DPO contribution, and source case groups

#### Scenario: Preserve execution and claim boundaries
- **WHEN** merge artifacts, reports, or Human Briefs describe the phase
- **THEN** they MUST state that strict `contract_exact_match` remains the primary metric
- **AND** they MUST state that no training, prediction, A100 execution, evaluator metric change, checkpoint release, or adapter release occurred
- **AND** they MUST NOT claim held-out recovery, model recovery, production readiness, private-corpus generalization, public full-corpus release, or live-browser benchmark improvement

### Requirement: Materialize form-fill confirmation-marker extension candidates separately
The system SHALL materialize reviewed form-fill confirmation-marker extension design cases into a public-safe candidate dataset that remains separate from the formal public sample until a later approved change explicitly merges it.

#### Scenario: Generate confirmation-marker extension candidate seeds
- **WHEN** the confirmation-marker extension materializer runs on a reviewed extension design artifact
- **THEN** it MUST write exactly one public-safe candidate seed row for each proposed candidate case
- **AND** each candidate seed MUST use a schema-valid Browser Task Contract with `task_type="form_fill"`, `route="fill_form"`, `confirmation_required=true`, and `safety.reason="requires_confirmation"`
- **AND** each candidate seed MUST include provenance linking back to the source design artifact, source case id, source family id, source bucket, field-label derivation status, and expected confirmation marker

#### Scenario: Preserve non-derivable field-label boundary
- **WHEN** a proposed candidate case has `field_label_derivation_status="not_derivable_from_committed_coverage_policy_artifacts"`
- **THEN** the materializer MUST NOT invent or expose private residual field labels
- **AND** the candidate provenance MUST label the field as a public-safe family-level candidate label rather than recovered gold text

#### Scenario: Expand candidate SFT rows without DPO
- **WHEN** confirmation-marker extension candidate seeds are generated
- **THEN** the materializer MUST expand them into candidate SFT rows using the existing SFT row schema and candidate provenance
- **AND** it MUST NOT generate DPO pairs or hard negatives in this phase

#### Scenario: Keep formal public sample unchanged
- **WHEN** confirmation-marker extension candidate materialization runs
- **THEN** it MUST NOT edit `data/public-samples/seed_traces.jsonl`, `sft_public_sample.jsonl`, `dpo_public_sample.jsonl`, or `manifest_public_sample.json`
- **AND** the materialization manifest MUST state `formal_public_sample_modified=false`, `seed_traces_modified=false`, `training_run=false`, `prediction_run=false`, `dpo_run=false`, `a100_execution=false`, and `evaluator_metric_change=false`

#### Scenario: Preserve evaluation and claim boundaries
- **WHEN** confirmation-marker extension candidate artifacts, reports, or Human Briefs describe the phase
- **THEN** they MUST state that strict `contract_exact_match`, strict `slot_f1`, and the contract evaluation ladder remain authoritative
- **AND** they MUST state that `slot_f1_soft` is diagnostic-only
- **AND** they MUST NOT claim held-out generalization recovery, model recovery, checkpoint release, adapter release, production readiness, private-corpus generalization, public full-corpus release, or live-browser benchmark improvement

### Requirement: Check form-fill confirmation-marker extension candidate integration preview
The system SHALL support a local preview integration check for standalone form-fill confirmation-marker extension candidate seeds before any later formal public sample merge, training, or held-out evaluation decision.

#### Scenario: Build preview dataset from extension candidates
- **WHEN** the preview integration check runs with the current formal public seed file and the standalone confirmation-marker extension candidate seed file
- **THEN** it MUST validate exactly the reviewed extension candidate seed rows
- **AND** it MUST build a report-scoped preview public dataset that combines formal seed rows plus the extension candidate seed rows
- **AND** it MUST record formal counts before preview, preview counts, preview split counts, candidate contribution counts, and candidate source identity

#### Scenario: Keep formal public sample unchanged
- **WHEN** the preview integration check runs
- **THEN** it MUST NOT edit `data/public-samples/seed_traces.jsonl`, `sft_public_sample.jsonl`, `dpo_public_sample.jsonl`, or `manifest_public_sample.json`
- **AND** the evidence manifest MUST state `formal_public_sample_modified=false`, `preview_only_not_formal_public_sample=true`, `training_run=false`, `prediction_run=false`, `a100_execution=false`, and `evaluator_metric_change=false`

#### Scenario: Validate preview artifacts
- **WHEN** the preview dataset is built
- **THEN** the check MUST validate the preview SFT, DPO, and manifest artifacts through the public dataset validator
- **AND** preview DPO pairs MUST be labeled as preview-only validation artifacts rather than committed formal DPO changes

#### Scenario: Preserve claim boundaries
- **WHEN** preview integration evidence, reports, or Human Briefs describe the phase
- **THEN** they MUST state that strict `contract_exact_match`, strict `slot_f1`, and the contract evaluation ladder remain authoritative
- **AND** they MUST state that `slot_f1_soft` is diagnostic-only
- **AND** they MUST NOT claim held-out generalization recovery, model recovery, checkpoint release, adapter release, production readiness, private-corpus generalization, public full-corpus release, or live-browser benchmark improvement

### Requirement: Merge form-fill confirmation-marker extension candidates into public sample
The system SHALL support a guarded formal merge of reviewed form-fill confirmation-marker extension candidate seeds into the committed public sample after candidate materialization and preview integration evidence exist.

#### Scenario: Merge reviewed extension candidates exactly once
- **WHEN** the merge command runs with the current formal public seed file and `form_fill_confirmation_marker_extension_seed_candidates.jsonl`
- **THEN** it MUST validate exactly the 12 reviewed confirmation-marker extension candidate seed rows
- **AND** it MUST fail if any candidate ID already exists in the formal public seed file
- **AND** it MUST append the candidate rows to the formal seed file without modifying unrelated formal rows

#### Scenario: Rebuild synchronized formal public artifacts
- **WHEN** the formal seed file is updated by the merge command
- **THEN** the system MUST rebuild `sft_public_sample.jsonl`, `dpo_public_sample.jsonl`, and `manifest_public_sample.json` from the updated formal seed file
- **AND** the resulting manifest MUST record 98 seed rows, 252 SFT rows, 850 DPO pairs, and split counts of train 114, dev 69, and test 69
- **AND** the derived artifacts MUST validate through the public dataset validator

#### Scenario: Publish merge evidence
- **WHEN** the merge completes
- **THEN** the system MUST publish JSON, Markdown, and manifest evidence under `reports/public-sample/`
- **AND** the evidence MUST record pre-merge counts, post-merge counts, candidate contribution counts, candidate source identity, validation status, and public-safety policy

#### Scenario: Preserve formal merge claim boundaries
- **WHEN** merge evidence, reports, or Human Briefs describe the phase
- **THEN** they MUST state that strict `contract_exact_match`, strict `slot_f1`, and the contract evaluation ladder remain authoritative
- **AND** they MUST state that `slot_f1_soft` is diagnostic-only
- **AND** they MUST NOT claim held-out generalization recovery, model recovery, checkpoint release, adapter release, production readiness, private-corpus generalization, public full-corpus release, or live-browser benchmark improvement
- **AND** they MUST state `training_run=false`, `prediction_run=false`, `a100_execution=false`, and `evaluator_metric_change=false`

### Requirement: Design blocked-payment safety repair candidates before materialization
The system SHALL publish public-safe design evidence for `blocked_payment`
safety repair candidates before materializing new safety seed rows, generating
new DPO pairs, or launching another training phase intended to address
`blocked_payment` false negatives.

#### Scenario: Derive candidates from committed safety diagnosis
- **WHEN** the candidate design reads the SFT v3 safety regression diagnosis
- **THEN** it MUST identify source row ids, source task family, failure
  classification, accepted safety target shape, and rejected drift shapes for
  each proposed `blocked_payment` repair candidate
- **AND** it MUST preserve support counts for regressed and persistent-miss rows

#### Scenario: Preserve design-only boundaries
- **WHEN** blocked-payment repair candidates are published for review
- **THEN** the evidence MUST state that it performs no public-sample mutation,
  local/private corpus mutation, SFT, DPO, GRPO, prediction generation, A100
  execution, prompt change, evaluator change, prediction repair, semantic
  scoring, adapter release, checkpoint release, production-readiness claim, or
  live-browser benchmark
- **AND** the evidence MUST include a `formal_public_sample_modified=false`
  boundary or equivalent machine-readable flag

#### Scenario: Recommend a bounded follow-up
- **WHEN** the design identifies candidate families with enough coverage to
  repair the observed `blocked_payment` misses
- **THEN** it MAY recommend a later bounded materialization or training phase
- **AND** it MUST NOT generate seed rows, DPO pairs, or model-quality claims as
  part of the design phase

### Requirement: Materialize reviewed blocked-payment safety repair candidates
The system SHALL materialize reviewed `blocked_payment` safety repair
candidates into public-safe seed rows and synchronized public derived artifacts
before any training or prediction phase uses them as data evidence.

#### Scenario: Materialize from reviewed candidate design
- **WHEN** the materialization phase reads the blocked-payment repair candidate design evidence
- **THEN** it MUST create public-safe seed rows for the reviewed repair families
- **AND** each materialized target contract MUST use `task_type=blocked`,
  `route=deny`, `safety.allow=false`, `safety.reason=unsafe_payment`, and
  `confirmation_required=false`
- **AND** the evidence MUST preserve candidate ids, repair families, source row
  ids, and source classification counts

#### Scenario: Rebuild synchronized public artifacts
- **WHEN** candidate seed rows are materialized
- **THEN** the system MUST rebuild the public manifest, SFT rows, and DPO pairs
  from the updated public seed traces
- **AND** the materialization evidence MUST record pre-materialization and
  post-materialization seed, SFT, and DPO counts
- **AND** public data validation and DPO family count checks MUST pass before
  the change is archived

#### Scenario: Preserve materialization-only boundaries
- **WHEN** materialization evidence, reports, or Human Briefs describe the phase
- **THEN** they MUST state that this phase performs no SFT, DPO, GRPO, A100
  execution, prediction generation, evaluator relaxation, semantic-equivalence
  scoring, prediction repair, prompt change, adapter release, checkpoint
  release, public full-corpus release, production-readiness claim, model-quality
  claim, or live-browser benchmark claim
- **AND** the evidence MUST include machine-readable boundary flags for those
  non-goals

### Requirement: Design current-retry confirmation-preservation candidates before materialization
The system SHALL publish a public-safe candidate-design artifact for
current-retry confirmation-preservation before modifying public sample seeds,
generating derived rows, or launching additional training.

#### Scenario: Derive candidates from trade-off diagnosis
- **WHEN** current SFT retry trade-off diagnosis evidence is available
- **THEN** the candidate design MUST identify source rows where confirmation
  regressed between the current-manifest baseline and the current-train-split
  retry
- **AND** each candidate family MUST record source row ids, source split,
  source task family, support counts, accepted target sketch, rejected drift
  sketches, and suggested public-safe utterance templates

#### Scenario: Preserve unsafe-payment confirmation target shape
- **WHEN** candidate design covers unsafe payment rows whose accepted target
  requires confirmation
- **THEN** accepted target sketches MUST preserve `task_type="blocked"`,
  `route="deny"`, `safety.allow=false`, `safety.reason="unsafe_payment"`,
  and `confirmation_required=true`
- **AND** rejected drift sketches MUST include variants that drop confirmation,
  allow the request as `form_fill/fill_form`, or otherwise weaken the unsafe
  payment denial target

#### Scenario: Preserve public navigation non-confirmation target shape
- **WHEN** candidate design covers public-readonly navigation rows whose
  accepted target does not require confirmation
- **THEN** accepted target sketches MUST preserve `task_type="navigate"`,
  `route="open_url"`, `safety.allow=true`, `safety.reason="public_readonly"`,
  and `confirmation_required=false`
- **AND** rejected drift sketches MUST include variants that drift toward
  `clarify/clarify`, require confirmation, or change the accepted canonical URL

#### Scenario: Keep design separate from data mutation
- **WHEN** confirmation-preservation candidate design evidence is published
- **THEN** it MUST state that no public seed rows, SFT rows, DPO pairs,
  manifest files, local/private corpora, prompts, evaluator metrics,
  predictions, checkpoints, or adapters were modified
- **AND** it MUST NOT claim model recovery, held-out recovery, safety
  improvement, production readiness, private-corpus generalization, or
  live-browser benchmark improvement

#### Scenario: Recommend a bounded next action
- **WHEN** the candidate design identifies sufficient candidate coverage
- **THEN** it MAY recommend one later bounded materialization phase
- **AND** it MUST NOT automatically materialize candidates, rebuild public
  sample artifacts, train, run DPO/GRPO, generate predictions, or change
  evaluator behavior as part of the design phase

### Requirement: Materialize reviewed current-retry confirmation-preservation candidates
The system SHALL materialize reviewed current-retry confirmation-preservation candidates into public-safe train seed rows and synchronized public derived artifacts while preserving data-only evidence boundaries.

#### Scenario: Materialize exactly reviewed candidate families
- **WHEN** the materialization phase reads the current-retry confirmation-preservation candidate design evidence
- **THEN** it MUST validate the design manifest id and materialize exactly the reviewed candidate families
- **AND** it MUST reject missing, extra, duplicate, unreviewed, or already-merged candidate rows
- **AND** each materialized seed MUST include provenance linking back to the source design, source candidate id, candidate family, source row ids, and accepted target sketch

#### Scenario: Preserve accepted confirmation targets
- **WHEN** unsafe-payment confirmation-preservation candidates are materialized
- **THEN** each accepted target contract MUST use `task_type=blocked`, `route=deny`, `safety.reason="unsafe_payment"`, and `confirmation_required=true`
- **AND** the materialization evidence MUST preserve the source row ids and rejected drift sketches for auditability
- **WHEN** public-navigation non-confirmation preservation candidates are materialized
- **THEN** each accepted target contract MUST use `task_type=navigate`, `route=open_url`, `safety.reason="public_readonly"`, and `confirmation_required=false`
- **AND** the materialization evidence MUST preserve the source row ids and rejected drift sketches for auditability

#### Scenario: Rebuild public sample artifacts
- **WHEN** confirmation-preservation candidate seed rows are materialized
- **THEN** the system MUST rebuild the public manifest, SFT rows, and DPO pairs from the updated formal public seed file
- **AND** the new manifest MUST record the updated seed, SFT, DPO, and split counts
- **AND** the materialization evidence MUST record pre-materialization and post-materialization counts plus candidate seed, SFT, and DPO contributions

#### Scenario: Preserve materialization-only boundaries
- **WHEN** materialization evidence, reports, or Human Briefs describe the phase
- **THEN** they MUST state that no training, prediction generation, prediction repair, prompt change, evaluator metric change, slot normalization, adapter release, checkpoint release, live-browser benchmark, or private corpus publication occurred
- **AND** they MUST NOT claim model recovery, held-out recovery, safety improvement, production readiness, or semantic-equivalence recovery

### Requirement: Design scaled public sample before materialization
The system SHALL publish a public-safe design artifact before expanding the formal public sample beyond the current manifest boundary.

#### Scenario: Produce scale-up target distribution
- **WHEN** a scaled public-sample design phase runs
- **THEN** it MUST report the current manifest id, current seed/SFT/DPO counts, current train/dev/test split counts, target seed-count milestone, and target family distribution
- **AND** it MUST identify task families, routes, safety reasons, confirmation behaviors, slot-key shapes, and accepted/rejected target-shape coverage that need additional examples

#### Scenario: Preserve design-only boundary
- **WHEN** scaled public-sample design evidence is generated
- **THEN** it MUST NOT mutate seed traces, SFT rows, DPO rows, manifests, model configs, prompts, evaluator metrics, prediction artifacts, or private corpora
- **AND** it MUST NOT claim model recovery, safety improvement, production readiness, checkpoint release, adapter release, private-corpus generalization, or live-browser benchmark improvement

#### Scenario: Keep future materialization reviewable
- **WHEN** the design recommends future data generation
- **THEN** it MUST separate candidate family names, accepted contract sketches, rejected drift sketches, augmentation-depth guidance, and validation gates so a later materialization phase can be reviewed before writing public sample files

#### Scenario: Preserve public-safe design artifacts
- **WHEN** scaled public-sample design artifacts are prepared for commit
- **THEN** validation MUST reject raw private rows, absolute local paths, private remote paths, host details, SSH details, secrets, tokens, raw logs, checkpoints, adapters, caches, and oversized generated corpora

### Requirement: Materialize scaled public-sample candidates
The system SHALL materialize deterministic, public-safe scaled public-sample
candidate seed rows and derived SFT sidecars from the archived scaled-sample
design without mutating the formal public sample.

#### Scenario: Generate standalone scaled candidates
- **WHEN** a developer runs scaled public-sample candidate materialization
- **THEN** the system writes standalone candidate seed rows, SFT candidate rows,
  a machine-readable manifest, and a human-readable report under candidate and
  report paths that are not the formal public sample files
- **AND** the candidate manifest MUST record that formal public sample files were
  not modified

#### Scenario: Preserve scaled target accounting
- **WHEN** scaled candidates are materialized from the current `102` seed
  boundary
- **THEN** the evidence MUST record current formal counts, target core counts,
  target overlay counts, candidate seed counts by family, candidate SFT row
  counts, and split counts
- **AND** the evidence MUST distinguish core-family candidates from
  confirmation-boundary overlay candidates

#### Scenario: Protect formal public sample files
- **WHEN** the materializer is given an output path
- **THEN** it MUST reject attempts to write candidate seeds, sidecars, or reports
  over `seed_traces.jsonl`, `sft_public_sample.jsonl`,
  `dpo_public_sample.jsonl`, or `manifest_public_sample.json`

#### Scenario: Bound candidate evidence claims
- **WHEN** reports or Human Briefs describe scaled candidate materialization
- **THEN** they MUST state that the phase does not merge the formal public
  sample, rebuild formal SFT/DPO artifacts, train, predict, change prompts,
  change evaluator metrics, normalize slots, repair predictions, release
  checkpoints/adapters, or prove model recovery

### Requirement: Merge scaled public-sample candidates into the formal public sample
The system SHALL support a guarded formal merge of reviewed scaled
public-sample candidate seeds into the committed public sample while preserving
candidate provenance, split labels, derived artifact synchronization, and
comparison-boundary warnings.

#### Scenario: Promote reviewed scaled candidates exactly once
- **WHEN** the merge command runs with the current formal public seed file and
  `scaled_public_sample_seed_candidates.jsonl`
- **THEN** it MUST validate exactly the reviewed 138 scaled candidate seed rows
- **AND** it MUST reject missing, extra, duplicate, already-formal, unreviewed,
  non-public-safe, or non-standalone candidate rows before rewriting formal
  public sample artifacts
- **AND** each promoted seed MUST use
  `source_mode="scaled_public_sample_formal_public_seed"`,
  `candidate_status="formal_public_sample"`, and a source reference to the
  candidate seed artifact
- **AND** each promoted seed MUST preserve its reviewed `train`, `dev`, or
  `test` split label

#### Scenario: Rebuild synchronized scaled formal artifacts
- **WHEN** scaled candidates are promoted into the formal public sample
- **THEN** the system MUST rebuild `seed_traces.jsonl`,
  `sft_public_sample.jsonl`, `dpo_public_sample.jsonl`, and
  `manifest_public_sample.json` from the updated formal seed file
- **AND** the rebuilt manifest MUST record 240 seed rows, 675 SFT rows, 2046 DPO
  pairs, and SFT split counts of train 261, dev 207, and test 207
- **AND** the manifest MUST summarize scaled candidate seed/SFT counts, group
  counts, family counts, and balanced candidate seed split counts
- **AND** the derived artifacts MUST validate through the public dataset
  validator

#### Scenario: Publish scaled merge evidence
- **WHEN** the scaled merge completes
- **THEN** the system MUST publish JSON, Markdown, and manifest evidence under
  `reports/public-sample/scaled-public-sample-merge/`
- **AND** the evidence MUST record pre-merge counts, post-merge counts,
  candidate seed/SFT/DPO contributions, DPO rejection deltas, validation status,
  execution scope, claim boundaries, and candidate source identity

#### Scenario: Preserve comparison and claim boundaries
- **WHEN** merge evidence, reports, manifests, tests, or Human Briefs describe
  the scaled formal merge
- **THEN** they MUST state that the formal public sample boundary changed and
  old metrics are not directly comparable
- **AND** they MUST state that strict `contract_exact_match`, strict `slot_f1`,
  and the contract evaluation ladder remain authoritative
- **AND** they MUST state that `slot_f1_soft` is diagnostic-only
- **AND** they MUST NOT claim held-out recovery, model quality improvement,
  safety improvement, model recovery, checkpoint release, adapter release,
  production readiness, private-corpus generalization, public full-corpus
  release, or live-browser benchmark improvement
- **AND** they MUST state `training_run=false`, `prediction_run=false`,
  `a100_execution=false`, `prompt_change=false`,
  `slot_normalization=false`, and `evaluator_metric_change=false`
