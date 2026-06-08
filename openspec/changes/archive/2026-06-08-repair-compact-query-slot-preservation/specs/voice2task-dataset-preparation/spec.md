## ADDED Requirements

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
