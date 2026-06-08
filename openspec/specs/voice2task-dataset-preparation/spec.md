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
