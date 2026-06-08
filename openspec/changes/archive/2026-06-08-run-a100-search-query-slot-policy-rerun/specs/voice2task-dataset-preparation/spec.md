## ADDED Requirements

### Requirement: Use current compact public search train targets for A100 rerun
The A100 search query slot-policy rerun SHALL use the current public sample train rows and SHALL preserve their compact public-readonly search targets in copied gold evidence.

#### Scenario: Copy train split gold rows
- **WHEN** `train_split_gold.jsonl` is generated for the rerun evidence pack
- **THEN** the three public search/weather train rows MUST use `slots={"query":"北京明天天气"}` and `normalized_command="搜索北京明天天气"`
- **AND** they MUST NOT contain `slots.city`, `slots.date`, `slots.topic`, or the artificial token-spaced query string `北京 明天 天气`
