## ADDED Requirements

### Requirement: Inspect SFT label provenance from training path
The system SHALL expose a public-safe SFT label provenance inspection result that distinguishes tokenizer/template evidence, collator evidence, true label tensor provenance, and assistant-target loss-mask evidence before SFT objective claims are interpreted.

#### Scenario: Report unavailable labels without inference
- **WHEN** objective inspection runs without an inspectable tokenizer/collator label source
- **THEN** the output MUST set true label evidence fields to unavailable values, record why labels were unavailable, and state that loss improvement alone does not prove Browser Task Contract learning

#### Scenario: Report inspectable collator labels
- **WHEN** objective inspection receives labels produced by the inspected training-tokenizer/collator path
- **THEN** the output MUST record the row id, label source, tokenizer/template status, collator status, prompt token count, assistant token count, prompt mask status, assistant-target loss status, and loss-interpretation boundary without writing raw rendered training text

#### Scenario: Preserve non-real fixture evidence boundary
- **WHEN** local validation uses fixture tokenizer/collator labels instead of the real training runtime
- **THEN** the output MUST label the evidence source as fixture or simulated and MUST NOT treat it as a real A100/private-adapter training proof

### Requirement: Keep label provenance inspection opt-in and non-heavy by default
The system SHALL keep label provenance inspection from downloading models, loading private adapters, or starting A100 execution unless a later explicitly scoped runtime phase authorizes it.

#### Scenario: Run default local inspection
- **WHEN** a developer runs the local objective or label provenance inspection command against the public-sample manifest without explicit runtime opt-ins
- **THEN** the command MUST inspect committed public-sample rows only, avoid private adapter loads and heavy training, and emit structured unavailable states for missing tokenizer/collator dependencies

#### Scenario: Bound runtime interpretation
- **WHEN** the inspection result is missing real tokenizer/collator label provenance
- **THEN** any report or metadata that references it MUST state that the result does not prove checkpoint release, adapter release, held-out generalization, production readiness, or live-browser improvement
