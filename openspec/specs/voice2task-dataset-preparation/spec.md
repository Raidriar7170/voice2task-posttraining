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
