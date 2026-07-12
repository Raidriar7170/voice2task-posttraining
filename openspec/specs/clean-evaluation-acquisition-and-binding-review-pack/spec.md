# clean-evaluation-acquisition-and-binding-review-pack Specification

## Purpose
Define the non-executable, public-safe acquisition and binding review-pack contract, including pure linting, fixed-path atomic publication, fail-closed recovery, explicit human-acceptance boundaries, and preparation-only evidence that cannot authorize freeze or execution.

## Requirements

### Requirement: Generate one canonical non-executable acquisition and binding review pack
The system SHALL generate a deterministic public-safe review pack that covers exactly the canonical clean-boundary input inventory without supplying executable values or becoming an alternative authority for execution semantics.

#### Scenario: Derive the exact binding catalog from the execution inventory
- **WHEN** the review pack is generated
- **THEN** its binding catalog MUST contain exactly 29 entries in the same order and with the same names as the authoritative clean-boundary execution inventory
- **AND** the generator MUST derive that catalog from the authoritative inventory rather than maintain a second hand-copied list
- **AND** repeated generation from identical inputs MUST produce byte-identical catalog, template, schema, checklist, summary, and manifest bytes

#### Scenario: Keep the committed template non-executable
- **WHEN** the committed review template is inspected or passed to an execution validator
- **THEN** it MUST use a distinct template schema version, set `template_only=true`, represent every unsupplied value or evidence item as `NOT_SUPPLIED`, and contain no syntactically valid fake authority or derivation hash
- **AND** each nested draft MUST use a distinct draft schema version, set `draft_only=true`, and wrap each proposed value in a draft-field record below `proposed_bindings` or `proposed_fields` so no object simultaneously reproduces a raw execution component/dossier key set and raw value layout
- **AND** the execution validator MUST fail closed for the whole envelope, every individually extracted draft, and every nested `proposed_*` map without returning a protocol hash or advancing any lifecycle state

### Requirement: Publish strict schemas without treating structure as authority
The system SHALL publish strict machine-readable schemas for the template/candidate envelope and its four nested draft sections while stating that schema conformance is not evidence of authority, independence, human review, binding, or freeze authorization.

#### Scenario: Reject unknown structural content
- **WHEN** a template or candidate component is checked against its published structural definition
- **THEN** every governed object MUST reject unknown properties, invalid types, missing required keys, and invalid enumerations
- **AND** the schema MUST distinguish template-only placeholders from candidate component shapes

#### Scenario: Keep structural validity below human acceptance
- **WHEN** one candidate envelope and all four nested draft sections are structurally valid
- **THEN** the result MUST NOT infer that authority labels are authentic, reviewers are independent in the real world, approvals were actually issued, or bindings took effect
- **AND** structural validity alone MUST leave `human_acceptance_status=NOT_RECORDED`, `freeze_authorized=false`, `next_phase_eligible=false`, and `execution_readiness=false`

### Requirement: Lint one non-executable candidate envelope through a pure pre-freeze semantic boundary
The system SHALL provide a non-mutating linter for one review envelope whose nested binding, source-contract, compiler-card, and model-card drafts reuse the authoritative execution validation semantics without exporting raw execution components or rendering or persisting a protocol.

#### Scenario: Report the empty-template preparation truth
- **WHEN** the committed template or a pack with no externally supplied candidate values is linted
- **THEN** the result MUST report `evidence_status=DESIGN_ONLY`, `phase_status=PREPARATION_ONLY`, `decision=ACQUISITION_AND_BINDING_REVIEW_PACK_READY_EXECUTION_BLOCKED`, `review_pack_status=READY_FOR_EXTERNAL_COMPLETION`, and `candidate_pack_status=INCOMPLETE`
- **AND** it MUST report `binding_inventory_count=29`, `supplied_binding_count=0`, `authoritatively_bound_binding_count=0`, `acquisition_source_status=UNAVAILABLE`, `current_readiness_state=DESIGN_ONLY`, `execution_bindings_status=INCOMPLETE`, `protocol_freeze_status=NOT_FROZEN`, `clean_population_status=NOT_MATERIALIZED`, and `boundary_integrity_status=NOT_CREATED`
- **AND** it MUST report `human_acceptance_status=NOT_RECORDED`, `freeze_authorized=false`, `next_phase_eligible=false`, and `execution_readiness=false`

#### Scenario: Cap a complete candidate at review required
- **WHEN** a temporary non-executable candidate envelope passes structural, existing semantic, and cross-component consistency checks
- **THEN** the linter MUST report `evidence_status=DESIGN_ONLY`, `phase_status=PREPARATION_ONLY`, `decision=CANDIDATE_PACK_STRUCTURALLY_COMPLETE_REVIEW_REQUIRED`, `review_pack_status=READY_FOR_EXTERNAL_COMPLETION`, and `candidate_pack_status=STRUCTURALLY_COMPLETE_REVIEW_REQUIRED`
- **AND** it MUST report `binding_inventory_count=29`, `supplied_binding_count=29`, `authoritatively_bound_binding_count=0`, and `acquisition_source_status=CANDIDATE_DECLARED_REVIEW_REQUIRED`
- **AND** it MUST keep `current_readiness_state=DESIGN_ONLY`, `execution_bindings_status=INCOMPLETE`, `protocol_freeze_status=NOT_FROZEN`, `clean_population_status=NOT_MATERIALIZED`, `boundary_integrity_status=NOT_CREATED`, `human_acceptance_status=NOT_RECORDED`, `freeze_authorized=false`, `next_phase_eligible=false`, and `execution_readiness=false`
- **AND** it MUST NOT return `protocol_sha256`, `READY_FOR_FREEZE`, `EXPERIMENT_BINDINGS_COMPLETE`, or any equivalent lifecycle or authorization claim

#### Scenario: Reject every unchanged draft surface at the freeze boundary
- **WHEN** the same complete candidate envelope, any individually extracted nested draft, or any nested `proposed_*` map is supplied unchanged to `freeze_protocol`, `validate_named_inputs`, the corresponding execution validator, or the existing clean-boundary validation CLI
- **THEN** it MUST fail before protocol serialization or persistence because no object exposed by the envelope is any of the four execution component schemas
- **AND** no protocol hash or protocol file may be produced

#### Scenario: Fail closed with sanitized gaps
- **WHEN** a candidate contains placeholders, missing or unknown fields, aliases, private-path values, invalid hashes, inconsistent provider/reviewer roles, unsupported power assumptions, or cross-component conflicts
- **THEN** the linter MUST return allowlisted blocker codes plus canonical section or field names only
- **AND** it MUST NOT echo candidate values, private paths, opaque identifiers, hashes, payload fragments, or raw exception text

#### Scenario: Separate lint conformance from execution authorization
- **WHEN** the CLI reports a complete envelope as `STRUCTURALLY_COMPLETE_REVIEW_REQUIRED`
- **THEN** it MUST exit zero with `lint_conforms=true`, omit a generic `ok` field, and keep `human_acceptance_status=NOT_RECORDED`, `freeze_authorized=false`, `next_phase_eligible=false`, and `execution_readiness=false`
- **AND** incomplete, invalid, unreadable, oversized, or unsafe input MUST exit nonzero with `lint_conforms=false`
- **AND** a zero lint exit MUST NOT be represented as binding, freeze, next-phase, or execution authorization

### Requirement: Enforce zero source-frame access and zero execution mutation
The system SHALL keep review-pack generation and linting outside every source-payload, lockbox-row, protocol-persistence, materialization, seal, row, arm, one-look, training, prediction, and experiment path.

#### Scenario: Expose only one review envelope to lint
- **WHEN** the candidate linter is invoked through a CLI or programmatic interface
- **THEN** the CLI MUST accept exactly one trusted-root-relative `clean-evaluation-review-envelope-v1` input below `data/local-private/clean-compiler-model-evaluation-boundary-v1/review-inputs/`, while the pure programmatic linter MAY accept an already parsed in-memory envelope
- **AND** any internal draft-to-component mapping MUST be ephemeral and discarded before return
- **AND** it MUST NOT accept, emit, export, serialize, or discover four standalone execution components, a source frame, lockbox attestation, lockbox row/member input, protocol hash, generation id, registry, membership, seal, evaluation row, model artifact, or experiment input

#### Scenario: Lint the committed template without crossing into private inputs
- **WHEN** the public committed template is generated
- **THEN** the generator MUST run the pure linter against its in-memory envelope before publication
- **AND** it MUST NOT reopen that template through the private-root CLI, copy it into the trusted review-input root, or create that root

#### Scenario: Leave private and protocol artifacts absent
- **WHEN** generation or lint succeeds, fails, or is interrupted
- **THEN** it MUST NOT create or modify the canonical private root, protocol directory or manifest, family registry, partition membership, population seal, evaluation rows, or arm artifacts
- **AND** source-frame and lockbox-row read counts MUST remain zero
- **AND** no compiler/model arm, one-look access, training, prediction, A100 execution, or experiment execution may occur

### Requirement: Make evidence ownership and human acceptance explicit
The system SHALL provide a review checklist that maps every candidate component and canonical binding to its responsible provider, independent reviewer, required source or derivation evidence, applicability, zero-access attestation, and human acceptance gate without pre-populating those facts.

#### Scenario: Require independent review roles in the checklist
- **WHEN** the checklist describes source and lockbox-lineage evidence
- **THEN** it MUST require distinct source provider and source reviewer roles and distinct lockbox validator and lockbox reviewer roles
- **AND** it MUST cover ancestry exclusions for public train/dev/test, remediation, challenge, prediction, and lockbox-v1 row content
- **AND** no role, approval, hash, statistical assumption, source digest, or review verdict may be pre-approved by the committed pack

#### Scenario: Prevent self-attestation from enabling a next phase
- **WHEN** a candidate supplies labels, hash-shaped strings, or `APPROVED` fields
- **THEN** those self-reported fields MUST NOT set `human_acceptance_status=RECORDED`, `freeze_authorized=true`, or `next_phase_eligible=true`
- **AND** a future change MUST separately record authentic provider/reviewer evidence and explicit human acceptance before proposing bind/freeze execution

### Requirement: Publish the fixed review bundle within an explicit exclusive-writer boundary
The system SHALL publish only `reports/public-sample/clean-evaluation-acquisition-and-binding-review-pack-v1/` through a descriptor-relative, create-once, exact-idempotent transaction under a trusted, exclusive, cooperative same-EUID review-writer assumption. The reserved transaction/recovery sibling prefix SHALL be `.review-pack-recovery-`. Throughout this requirement, a promise of no namespace, content, or capability-issued metadata mutation excludes only filesystem-managed access-time changes caused solely by descriptor reads. This requirement SHALL NOT claim portable POSIX compare-and-delete behavior, add or strengthen any legacy public-evidence threat/recovery/update guarantee, or grant binding, freeze, materialization, or other lifecycle authority.

#### Scenario: Preflight one pre-existing trusted namespace
- **WHEN** review publication or current-bundle verification starts
- **THEN** `reports/public-sample` MUST already exist and the writer MUST NOT create the trusted root, any ancestor, or the fixed parent
- **AND** the trusted root, every pre-existing ancestor, and the fixed parent MUST be directories owned by the effective UID, MUST NOT be group- or other-writable, and MUST retain stable linked/opened/relinked device, inode, type, UID, GID, and mode observations
- **AND** the writer MUST record the fixed parent's GID as the trusted parent policy for the final directory
- **AND** preflight rejection MUST perform no namespace, content, or capability-issued metadata mutation; filesystem-managed access-time changes caused solely by descriptor reads are the only exclusion from this observable contract

#### Scenario: Block current state when any reserved sibling exists
- **WHEN** any sibling under the fixed parent has the `.review-pack-recovery-` prefix
- **THEN** publication success, current-evidence classification, and task 3.2 MUST remain blocked whether or not that sibling's identity can be verified
- **AND** the writer MUST return sanitized code `REVIEW_PUBLICATION_RECOVERY_PRESENT` without performing namespace, content, or capability-issued metadata mutation on that sibling
- **AND** the blocker MUST require separate manual disposition because automatic garbage collection is out of scope

#### Scenario: Preflight supported atomic no-replace capability
- **WHEN** the fixed final is absent
- **THEN** Darwin MUST expose the required `renameatx_np` no-replace implementation/symbol or Linux MUST expose the required `renameat2` no-replace implementation/symbol before any staging state is created
- **AND** any other platform or missing implementation/symbol MUST fail with sanitized code `REVIEW_PUBLICATION_NO_REPLACE_UNAVAILABLE` before staging
- **AND** that failure MUST perform no namespace, content, or capability-issued metadata mutation
- **AND** no ordinary rename or replace fallback may run

#### Scenario: Treat one mechanically exact existing bundle as a verified no-op
- **WHEN** the fixed final exists and no reserved-prefix sibling exists
- **THEN** the fixed-final directory MUST retain unchanged linked/opened/relinked device, inode, type, UID, GID, and mode observations, have mode `0755`, be owned by the effective UID, use the fixed parent's trusted GID, and have no group/other write bits
- **AND** its names MUST equal the exact expected seven-member set
- **AND** each member MUST be regular, mode `0644`, and link count one, and MUST be opened with `O_NOFOLLOW`
- **AND** each member MUST be read with an explicit bound no larger than its expected payload length plus one byte, compare byte-identically to the deterministic payload, and retain unchanged pre/post `fstat` plus linked/relinked device, inode, type, UID, GID, mode, link count, size, `mtime_ns`, and `ctime_ns` observations
- **AND** only after every check passes MAY the writer return the existing bundle as a no-op
- **AND** it MUST create no staging state and perform no namespace, content, or capability-issued metadata mutation, promotion, exchange, `unlinkat`, `rmdir`, destructive cleanup, or ordinary fallback

#### Scenario: Reject changed or partial existing state without repair
- **WHEN** the fixed final has changed bytes, a missing member, an extra member, a partial bundle, a wrong directory/member mode, a wrong owner/GID policy, an unexpected link count, or any other mismatch from the mechanically exact bundle
- **THEN** the writer MUST fail before creating staging state or performing namespace, content, or capability-issued metadata mutation
- **AND** only filesystem-managed access-time changes caused solely by descriptor reads are excluded; exchange, `unlinkat`, `rmdir`, destructive cleanup, repair, promotion, and ordinary fallback MUST NOT run

#### Scenario: Reject pre-existing redirected or unsafe state before mutation
- **WHEN** the trusted root, any ancestor, the fixed parent, the fixed final, or any member is a symlink, non-directory/non-regular object, unexpected hardlink, pre-existing competing destination, or exchanged identity
- **THEN** the writer MUST reject it before creating staging state or performing namespace, content, or capability-issued metadata mutation
- **AND** once identity uncertainty is observed for an object, the writer MUST perform no further pathname, content, or capability-issued metadata mutation on that uncertain object
- **AND** it MUST leave the canonical private root and every unrelated file unchanged

#### Scenario: Publish an absent final with atomic no-replace
- **WHEN** the trusted namespace, zero-reserved-sibling gate, supported-platform gate, and absent-final preflight all pass
- **THEN** the writer MUST pre-verify as absent a name formed from `.review-pack-recovery-` plus at least 128 CSPRNG bits, such as 32 lowercase hexadecimal characters
- **AND** it MUST create and keep that directory as `0700` while retaining an open descriptor, write and fsync exactly the seven deterministic regular `0644` single-link members, and fsync the staging directory
- **AND** only after all member writes and fsyncs succeed, immediately before promotion, it MUST use the retained directory descriptor to set mode `0755`
- **AND** post-`fchmod` `fstat` plus relinked checks MUST prove the same directory, mode `0755`, UID equal to the effective UID, GID equal to the trusted parent policy, and no group/other write bits
- **AND** it MUST fsync the staging directory and fixed parent again before using only the supported descriptor-relative atomic no-replace primitive
- **AND** the successful path MUST leave zero reserved-prefix siblings and MUST NOT call exchange, `unlinkat`, `rmdir`, destructive cleanup, or ordinary fallback

#### Scenario: Preserve a competitor inserted after preflight
- **WHEN** another writer inserts the fixed final after absent-final preflight but before promotion
- **THEN** atomic no-replace MUST fail, the competing final MUST receive no namespace, content, or capability-issued metadata mutation from this writer, and the invocation MUST fail
- **AND** if the unpromoted staging directory still satisfies transaction-owned recovery proof, the writer MUST retain it under the mechanical recovery rule and return `REVIEW_PUBLICATION_RECOVERY_RETAINED`

#### Scenario: Retain owned staging after a filesystem no-replace failure
- **WHEN** the platform implementation/symbol preflight passed but the filesystem-specific no-replace operation fails after staging was created and promotion is not proven successful
- **THEN** no ordinary fallback may run
- **AND** provably transaction-owned staging MUST be retained under the mechanical recovery rule and the invocation MUST fail with `REVIEW_PUBLICATION_RECOVERY_RETAINED`

#### Scenario: Prove and retain transaction-owned recovery mechanically
- **WHEN** failure occurs after staging creation but before promotion is proven successful
- **THEN** staging is transaction-owned only if this invocation pre-verified its full reserved name as absent, retained an open descriptor from creation, and linked/opened/`fstat`/relinked device, inode, type, UID, and GID observations agree
- **AND** when that proof holds, the writer MUST use the retained descriptor to set or restore mode `0700`
- **AND** post-`fchmod` `fstat` plus relinked checks MUST prove the same directory, mode `0700`, UID equal to the effective UID, and GID equal to the trusted parent policy before the sibling is retained
- **AND** the writer MUST retain that verified sibling and MUST return sanitized code `REVIEW_PUBLICATION_RECOVERY_RETAINED`
- **AND** automatic garbage collection MUST remain out of scope

#### Scenario: Stop mutating an identity-uncertain object
- **WHEN** transaction ownership or current object identity cannot be proved
- **THEN** the writer MUST perform no further pathname, content, or capability-issued metadata mutation on that uncertain object
- **AND** it MUST NOT classify that object as transaction-owned recovery
- **AND** it MUST return sanitized code `REVIEW_PUBLICATION_IDENTITY_UNCERTAIN` without leaking a path, token, inode, UID, GID, payload, or raw exception

#### Scenario: Classify post-syscall wrapper errors by inspection only
- **WHEN** a wrapper reports an error after invoking a namespace syscall
- **THEN** the writer MUST first use observation-only checks and MUST NOT assume that the syscall did not run
- **AND** only a proven unpromoted transaction-owned staging directory MAY receive descriptor-only mode `0700` recovery handling
- **AND** a proven promoted final MUST NOT be rolled back, cleaned, or downgraded to mode `0700`, and the invocation MUST return sanitized code `REVIEW_PUBLICATION_POST_SYSCALL_FAILURE`
- **AND** an outcome that cannot be proved MUST follow `REVIEW_PUBLICATION_IDENTITY_UNCERTAIN`

#### Scenario: Scope malicious same-EUID mutation outside the review guarantee
- **WHEN** publication guarantees are evaluated
- **THEN** they MUST assume no malicious or concurrent same-EUID process mutates governed names except for the explicitly tested post-preflight competing insertion
- **AND** other same-EUID replacement MUST be classified as account/process-boundary compromise rather than portable CAS protection supplied by this capability
- **AND** no-follow, identity, random-name, restrictive-mode, and post-operation checks MUST be described as defense-in-depth only

### Requirement: Publish a truthful preparation-only evidence surface
The system SHALL publish deterministic aggregate-only preparation evidence that remains subordinate to the archived S0 boundary result and contains no private candidate content.

#### Scenario: Preserve the archived S0 blocker
- **WHEN** the review-pack evidence is added to current navigation and the evidence index
- **THEN** its evidence-index classification MUST use the existing `DESIGN_ONLY` vocabulary and state that the pack is operator guidance rather than a source, reviewed binding packet, frozen protocol, clean population, or executable experiment
- **AND** the archived execution result MUST remain `evidence_status=BLOCKED`, `decision=CLEAN_EVALUATION_BOUNDARY_MATERIALIZATION_BLOCKED`, and `current_readiness_state=DESIGN_ONLY`
- **AND** its five-file blocker bundle MUST remain current, byte-identical, and not superseded by this phase

#### Scenario: Keep the public bundle safe and reproducible
- **WHEN** the public pack, summaries, manifest, and Human Brief are generated
- **THEN** they MUST contain only canonical field names, public instructions, allowlisted states, aggregate gap counts, and artifact hashes
- **AND** they MUST exclude supplied candidate values, private paths, member ids, source records, row text, audio, transcript, annotation, gold, prediction, outcome, lockbox rows or member hashes, credentials, host details, and raw logs
- **AND** deterministic regeneration, link validation, leak scanning, protected-hash comparison, and current-truth checks MUST pass before the evidence is current
