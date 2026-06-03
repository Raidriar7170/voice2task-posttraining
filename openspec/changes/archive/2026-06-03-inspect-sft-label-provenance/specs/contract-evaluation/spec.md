## ADDED Requirements

### Requirement: Publish public-safe SFT label provenance evidence
The system SHALL publish a public-safe SFT label provenance evidence pack that summarizes objective inspection provenance, label-mask status, evidence gaps, prior diagnostic links, and claim boundaries without exposing private runtime details.

#### Scenario: Generate label provenance evidence pack
- **WHEN** label provenance inspection output is prepared for committed evidence
- **THEN** the system MUST write machine-readable JSON and human-readable Markdown that report inspection status, label source, tokenizer/template status, collator status, prompt mask status, assistant-target loss status, evidence gaps, and prior diagnostic artifact links

#### Scenario: Keep evidence public-safe
- **WHEN** label provenance evidence is prepared for commit
- **THEN** leak-scan validation MUST reject raw private rows, local or remote private paths, secrets, private IP addresses, SSH details, raw logs, checkpoints, adapters, caches, oversized generated corpora, and private remote paths

#### Scenario: Bound label provenance interpretation
- **WHEN** public documentation or Human Briefs describe label provenance evidence
- **THEN** they MUST state whether true labels were inspected or unavailable and MUST NOT claim model recovery, held-out generalization, checkpoint release, adapter release, production readiness, or live-browser improvement
