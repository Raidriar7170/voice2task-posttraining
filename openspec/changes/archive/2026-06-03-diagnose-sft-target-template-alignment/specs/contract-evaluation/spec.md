## ADDED Requirements

### Requirement: Publish SFT target-template alignment evidence
The system SHALL publish a public-safe SFT target-template alignment evidence pack that links prior train-split failure evidence to training-target, prompt-template, label-mask, and adapter/base diagnostic findings without repairing or replacing predictions.

#### Scenario: Generate alignment evidence pack
- **WHEN** the local alignment diagnostic runs against committed public-sample rows, config templates, prior prediction metadata, and prior objective-inspection evidence
- **THEN** it MUST write machine-readable JSON and human-readable Markdown that summarize training-vs-prediction prompt alignment, assistant target span status, label-mask evidence status, chat-template evidence status, adapter/base metadata alignment, and evidence gaps

#### Scenario: Link prior failed diagnostic without changing it
- **WHEN** the alignment report references the prior A100 train-split diagnostic
- **THEN** it MUST link the prior prediction, metrics, objective-inspection, and report artifacts and MUST NOT alter, repair, normalize, coerce, or replace prior private-adapter prediction rows

#### Scenario: Keep alignment evidence public-safe
- **WHEN** SFT target-template alignment evidence is prepared for commit
- **THEN** leak-scan validation MUST reject raw private rows, local or remote private paths, secrets, private IP addresses, SSH details, raw logs, checkpoints, adapters, caches, oversized generated corpora, and private remote paths

#### Scenario: Bound alignment interpretation
- **WHEN** public documentation or Human Briefs describe the SFT target-template alignment diagnostic
- **THEN** they MUST state that the evidence narrows local formatting and metadata gaps only and does not prove model recovery, held-out generalization, release readiness, production readiness, or live-browser improvement
