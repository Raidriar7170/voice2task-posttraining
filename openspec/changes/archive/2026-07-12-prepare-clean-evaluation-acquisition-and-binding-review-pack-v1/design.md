## Context

The archived `materialize-and-freeze-clean-compiler-model-evaluation-boundary-v1` change implemented the authoritative bind/freeze/materialize/seal path and then correctly stopped at S0: no independent metadata-only source exists, 0/29 bindings are complete, the protocol is not frozen, and no private registry, membership, or seal exists. The implementation owns the exact 29-field inventory and strict semantic validators; the only complete examples currently live in test helpers and use synthetic hashes and values that are not project evidence.

The existing `clean-boundary-validate` command is not a preparation linter. Its path calls protocol freeze and persists a protocol manifest after validation. Reusing it for intake review would risk turning structurally plausible or self-attested inputs into a frozen lifecycle state. This change therefore needs a separate public review-pack capability with a pure, non-mutating lint boundary.

The stakeholders are an external source provider, an independent source reviewer, statistical reviewers for the compiler and model cards, the repository operator, and the later bind/freeze change reviewer. Public artifacts must remain sanitized; real candidate values, private paths, source-frame content, and reviewer evidence stay outside the committed pack.

## Goals / Non-Goals

**Goals:**

- Publish one deterministic, public-safe pack that explains every required input and every independent review gate without supplying fake values.
- Keep the canonical 29-field inventory and semantic rules single-sourced from the existing execution implementation.
- Provide strict structural schemas, a template-only intake document, a responsibility/evidence checklist, and sanitized gap reports.
- Provide a pure linter that assesses one non-executable candidate envelope without exporting raw execution components, freezing or persisting a protocol, or reading a source frame or lockbox rows.
- Preserve exact preparation-only truth and make human acceptance a separate, explicit future fact.

**Non-Goals:**

- Obtaining, selecting, generating, or substituting a real acquisition source or source-frame digest.
- Recording real provider/reviewer identity evidence, authority approvals, statistical choices, or any of the 29 binding values in committed artifacts.
- Freezing or persisting a protocol; creating or modifying the canonical private root, family registry, membership, seal, rows, or arm artifacts; or accessing one-look data.
- Changing the existing clean-boundary lifecycle, validators' accept/reject semantics, CLI success semantics, prompt, decoding, contract schema, evaluator, runtime, public dataset, or lockbox.
- Training, prediction, A100 execution, experiment execution, generic chat fine-tuning, skill routing, GUI action-policy learning, first-phase GRPO, checkpoint/full-corpus release, or any model, compiler, executable, natural-ASR, safety, production, or live-browser improvement claim.

## Decisions

### 1. Add a separate preparation capability

The new capability is `clean-evaluation-acquisition-and-binding-review-pack`. It consumes the existing boundary's inventory and pure validation rules but does not modify the `clean-compiler-model-evaluation-boundary` specification or own any lifecycle transition. The archived S0 report remains current evidence and is not superseded.

Alternative considered: add template behavior directly to the execution capability. Rejected because it would blur the distinction between operator guidance and authoritative bind/freeze semantics, making a committed template easier to misread as an executable packet.

### 2. Publish one deterministic public bundle

Apply will generate `reports/public-sample/clean-evaluation-acquisition-and-binding-review-pack-v1/` with this bounded surface:

- `binding-catalog.json`: the ordered 29-field catalog plus review responsibilities and required evidence fields, with no values;
- `review-pack.schema.json`: strict JSON Schema with separate template/candidate-envelope `$id` values, an explicit draft, `additionalProperties=false` throughout, and nested definitions for the envelope and its four non-exportable draft sections;
- `review-pack.template.json`: the single fillable envelope, marked `template_only=true`, `NOT_AN_EXECUTION_INPUT`, and `NO_HUMAN_ACCEPTANCE_RECORDED`, whose target values and evidence fields are `NOT_SUPPLIED` rather than plausible defaults or syntactically valid fake hashes;
- `review-checklist.md`: source ancestry/exclusion, provider/reviewer independence, statistical-review, zero-access, and human-acceptance checks;
- `summary.json` and `summary.md`: the exact preparation-only truth and current gaps; and
- `manifest.json`: deterministic hashes of the other bundle members, excluding runtime timestamps and avoiding a self-hash cycle.

The generator derives the catalog from `EXECUTION_BINDING_FIELDS`; it does not maintain a hand-copied second inventory. Repeated generation from identical code and inputs must produce byte-identical artifacts. Neither generation nor lint writes four standalone execution components or offers an export/conversion function.

Alternative considered: publish four apparently executable example JSON files copied from test fixtures. Rejected because their plausible values and hashes would invite accidental reuse as authority evidence and could falsely suggest that S0 is resolved.

### 3. Treat JSON Schema as structural documentation only

The schema makes object shape, types, exact keys, enumerations, and placeholder/template separation inspectable to external reviewers. It does not establish authority authenticity, source independence, human acceptance, binding effectiveness, protocol freeze, or execution eligibility. The committed template validates only against the template wrapper and must fail when passed to the execution packet validators.

Core generation and linting remain dependency-free. The JSON Schema artifact may be checked in tests when the existing optional `jsonschema` dependency is available, but the production CLI does not gain an unconditional dependency. Semantic acceptance continues to come from the existing pure Python rules.

### 4. Extract one pure pre-freeze validation seam

Apply will factor the current binding, source-contract, power-card, and cross-component checks into a shared pure function used by both the review linter and the existing freeze path. The function returns only validation/gap facts; it does not serialize a protocol, calculate or return `protocol_sha256`, persist a manifest, or mutate any path. The execution freeze path calls this seam before performing its existing canonical render and persistence, preserving one semantic authority.

Alternative considered: duplicate the validators in a review-pack module. Rejected because the template and execution contracts would drift and a review pack could pass rules that the real freeze path rejects.

### 5. Use two conservative lint outcomes

The committed empty template and ordinary generated summary use:

- `evidence_status=DESIGN_ONLY`;
- `phase_status=PREPARATION_ONLY`;
- `decision=ACQUISITION_AND_BINDING_REVIEW_PACK_READY_EXECUTION_BLOCKED`;
- `review_pack_status=READY_FOR_EXTERNAL_COMPLETION`;
- `candidate_pack_status=INCOMPLETE`;
- `binding_inventory_count=29`, `supplied_binding_count=0`, and `authoritatively_bound_binding_count=0`;
- `acquisition_source_status=UNAVAILABLE`;
- `current_readiness_state=DESIGN_ONLY`;
- `execution_bindings_status=INCOMPLETE`;
- `protocol_freeze_status=NOT_FROZEN`;
- `clean_population_status=NOT_MATERIALIZED`;
- `boundary_integrity_status=NOT_CREATED`;
- `human_acceptance_status=NOT_RECORDED`;
- `freeze_authorized=false`, `next_phase_eligible=false`, and `execution_readiness=false`.

A temporary candidate envelope whose four nested drafts pass structural, semantic, and cross-component checks reports `evidence_status=DESIGN_ONLY`, `phase_status=PREPARATION_ONLY`, `decision=CANDIDATE_PACK_STRUCTURALLY_COMPLETE_REVIEW_REQUIRED`, `review_pack_status=READY_FOR_EXTERNAL_COMPLETION`, `candidate_pack_status=STRUCTURALLY_COMPLETE_REVIEW_REQUIRED`, `binding_inventory_count=29`, `supplied_binding_count=29`, `authoritatively_bound_binding_count=0`, and `acquisition_source_status=CANDIDATE_DECLARED_REVIEW_REQUIRED`. It still reports `current_readiness_state=DESIGN_ONLY`, `execution_bindings_status=INCOMPLETE`, `protocol_freeze_status=NOT_FROZEN`, `clean_population_status=NOT_MATERIALIZED`, `boundary_integrity_status=NOT_CREATED`, `human_acceptance_status=NOT_RECORDED`, `freeze_authorized=false`, `next_phase_eligible=false`, and `execution_readiness=false`. Self-reported authority labels, hashes, and `APPROVED` fields cannot prove that the named external parties exist or accepted the packet.

Alternative considered: return `READY_FOR_FREEZE` after semantic lint. Rejected because software can validate grammar and internal consistency but cannot establish real-world authority, independence, or human acceptance from self-asserted fields.

### 6. Use one non-executable candidate envelope

`review-pack.template.json` and every externally completed draft use root schema `clean-evaluation-review-envelope-v1`. The empty template has `template_only=true`; a filled draft sets `template_only=false` but remains an envelope containing nested `binding_draft`, `source_contract_draft`, `compiler_card_draft`, and `model_card_draft` sections.

Each nested section is itself a wrapper with a distinct `*-draft-v1` schema version, `draft_only=true`, a declarative target-schema label, and `proposed_bindings` or `proposed_fields` rather than the raw execution component's exact top-level shape. Proposed maps may retain canonical field names for operator usability, but every value is a draft-field record containing `proposed_value` plus evidence/review placeholders. No envelope object or subobject may simultaneously reproduce a raw component/dossier key set and its raw value layout. Therefore neither the envelope, an individually extracted draft, nor its `proposed_*` map is valid as an execution binding packet, source contract, compiler card, or model card. The linter may map proposed draft-field records to ephemeral component dictionaries in memory solely to call the shared semantic seam; it must discard that mapping and expose no serializer, return value, or file export for it.

The linter accepts exactly one envelope through `voice2task-data clean-boundary-review-lint --review-pack <name>`. It validates the nested sections in memory through the shared pure semantic seam, but neither its API nor CLI returns or writes the ephemeral raw components. Passing either the complete envelope or any one extracted nested draft unchanged to `freeze_protocol`, `validate_named_inputs`, the corresponding execution validator, or `clean-boundary-validate` must fail before protocol rendering or persistence and must produce neither a protocol hash nor a protocol file.

The CLI's sole trusted input root is the fixed constant `data/local-private/clean-compiler-model-evaluation-boundary-v1/review-inputs/`. The explicit envelope read reuses the bounded descriptor-relative named-file policy below that already existing root; it does not create or modify the root, discover sibling files, or follow a source-frame reference. The public committed template is linted in memory by the pure generator/linter before publication rather than reopened through the private-root CLI. The CLI does not accept four raw component paths, `source-frame`, lockbox-attestation, generation, protocol-hash, membership, seal, row, model, or experiment arguments. Diagnostics contain only public blocker codes, section names, and missing canonical field names; stdout and stderr never echo supplied values, paths, identifiers, hashes, raw exceptions, tracebacks, or payload fragments.

`clean-boundary-review-lint` exits 0 only when an envelope conforms to draft structural, semantic, and cross-component checks; its output uses `lint_conforms=true` and the required `STRUCTURALLY_COMPLETE_REVIEW_REQUIRED` truth, omits a generic `ok` field, and keeps human acceptance, freeze authorization, next-phase eligibility, and execution readiness false. Incomplete, invalid, unreadable, oversized, or unsafe inputs exit nonzero with `lint_conforms=false`. Exit 0 is lint conformance only, never bind/freeze authorization.

Converting the `proposed_*` draft structures into four executable components and recording an independent acceptance receipt require a later separately reviewed change with `HUMAN_ACCEPTANCE_RECORDED`; this phase has no conversion path.

### 7. Use a mechanically bounded create-once publication policy

The fixed review path is `reports/public-sample/clean-evaluation-acquisition-and-binding-review-pack-v1/`, and the reserved transaction/recovery sibling prefix is `.review-pack-recovery-`. The short decision is: verify a pre-existing trusted namespace, publish an absent final once with a supported atomic no-replace primitive, treat one mechanically exact existing bundle as a no-op, and otherwise fail with no review-path repair or destructive cleanup.

**Observable preflight boundary.** `reports/public-sample` must already exist; the review writer does not create the trusted root, ancestors, or fixed parent. The trusted root, every pre-existing ancestor, and the fixed parent must be directories owned by the effective UID, must not be group- or other-writable, and must retain the same linked/opened/relinked device, inode, type, UID, GID, and mode throughout preflight. The fixed parent's GID is the trusted parent policy used for the final directory. Before classifying either an absent or exact-existing final, the writer lists the fixed parent and requires zero siblings with the reserved recovery prefix. Pre-existing unsafe, redirected, changed, partial, or recovery-blocked state fails with no namespace, content, or capability-issued metadata mutation. Filesystem-managed access-time changes caused solely by descriptor reads are the only exclusion from this observable no-mutation contract.

**Supported atomic primitive.** Before creating staging state, Darwin must expose the no-replace `renameatx_np` implementation/symbol and Linux must expose `renameat2` with no-replace support. Other platforms, or a missing implementation/symbol, fail with sanitized code `REVIEW_PUBLICATION_NO_REPLACE_UNAVAILABLE`. There is no ordinary rename/replace fallback. A filesystem-specific no-replace failure that occurs only after verified staging exists follows the owned-recovery rule below and still fails.

**Mechanically exact existing bundle.** Current/no-op requires zero reserved-prefix siblings plus a fixed-final directory whose linked/opened/relinked device, inode, type, UID, GID, and mode remain stable, whose mode is `0755`, whose UID equals the effective UID, whose GID equals the trusted parent policy, and whose group/other write bits are clear. Its names must equal the exact seven-member set. Each member must be regular, mode `0644`, and link count one; it is opened with `O_NOFOLLOW`, read with an explicit byte bound, compared byte-for-byte with the deterministic expected payload, and checked with pre/post `fstat` plus linked/relinked identity so device, inode, type, UID, GID, mode, link count, size, `mtime_ns`, and `ctime_ns` remain unchanged across the read. Only this complete observation may return the existing bundle as a no-op, with no namespace, content, or capability-issued metadata mutation. Any changed, missing, extra, partial, unsafe, or identity-drifting final fails under the same no-mutation contract.

**Absent publication and competing insertion.** With a verified absent final, the writer pre-verifies a reserved sibling name as absent, where the name is the reserved prefix plus at least 128 bits from a CSPRNG (for example, 32 lowercase hexadecimal characters). It creates and keeps that directory as `0700` while retaining an open descriptor, writes and fsyncs the exact seven members, and fsyncs the staging directory. Only immediately before promotion, after all member writes and fsyncs succeed, it uses the retained directory descriptor to `fchmod` staging to `0755`; `fstat` plus relinked checks must then prove the same directory, mode `0755`, UID equal to the effective UID, GID equal to the trusted parent policy, and no group/other write bits. It fsyncs the directory and fixed parent again before using the supported descriptor-relative atomic no-replace primitive. If a competitor inserts the final after preflight, no-replace must fail, the competitor receives no namespace, content, or capability-issued metadata mutation, and a still-provably-owned staging directory follows the recovery rule. The review path never calls exchange, `unlinkat`, `rmdir`, destructive cleanup, or an ordinary fallback.

**Mechanical recovery ownership and fixed failures.** A sibling is transaction-owned only when this invocation pre-verified its full reserved name as absent, created it while retaining an open descriptor, and linked/opened/`fstat`/relinked observations agree on device, inode, type, UID, and GID. If failure occurs after staging creation but before promotion is proven successful and that ownership remains provable, the writer must use the retained descriptor to set or restore mode `0700`; a new `fstat` plus relinked check must prove the same directory, mode `0700`, UID equal to the effective UID, and GID equal to the trusted parent policy before it is retained with sanitized code `REVIEW_PUBLICATION_RECOVERY_RETAINED`. If identity cannot be proved, the writer performs no further pathname, content, or capability-issued metadata mutation on that uncertain object, does not classify it as recovery, and returns sanitized code `REVIEW_PUBLICATION_IDENTITY_UNCERTAIN`.

**Post-syscall and current classification.** A wrapper error after a syscall triggers observation-only outcome classification first; the writer never assumes that the syscall did not run. Only after observation proves that the owned staging directory remains unpromoted may the descriptor-only `0700` recovery action run. A proven promoted final is not rolled back, cleaned, or downgraded to `0700`, and the invocation returns `REVIEW_PUBLICATION_POST_SYSCALL_FAILURE`; an outcome that cannot be proved follows `REVIEW_PUBLICATION_IDENTITY_UNCERTAIN`. Any sibling under the fixed parent whose name has the reserved recovery prefix blocks publication success, current-evidence classification, and task 3.2 regardless of whether that sibling's identity can be verified. It returns sanitized code `REVIEW_PUBLICATION_RECOVERY_PRESENT` until a separate manual disposition removes the blocker. Automatic garbage collection is out of scope.

**Threat and legacy boundaries.** Review publication assumes a trusted, exclusive, cooperative same-EUID writer; same-EUID malicious namespace mutation is an account/process-boundary compromise, and identity/random-name checks are defense-in-depth rather than portable pathname CAS. This capability adds or strengthens no threat, recovery, retention, cleanup, rollback, or update guarantee for `write_public_evidence`. Legacy regression acceptance is limited to its observable signature, five names/order/bytes, `0644`/single-link outputs, changed-update success, no new sibling on normal success, and public-safe error surface. A formal legacy threat model requires a separate change, and the legacy path gains no review-pack lifecycle authority.

### 8. Preserve current evidence and protected bytes

The new evidence-index entry uses the existing `DESIGN_ONLY` classification and explicitly says that the pack is operator guidance, not a source, binding packet, frozen protocol, clean population, or experiment. The archived S0 five-file report bundle, public dataset, lockbox aggregates, prompts, contract schema, evaluator, and runtime must remain byte-identical. Navigation files may receive separately reviewed additive entries, but their existing S0 entries and exact truth values must not change.

The Human Brief generated during apply must distinguish `review pack ready` from `candidate reviewed`, `human acceptance recorded`, and `protocol frozen`.

## Risks / Trade-offs

- [A polished template may be mistaken for approved evidence] → Use a distinct template schema version, `template_only=true`, `NOT_SUPPLIED`, no valid-looking hashes, fixed blocked truth, and tests proving execution-validator rejection.
- [The schema and runtime validators may drift] → Derive the catalog from the execution constant and share a pure semantic validation seam; add exact-parity tests.
- [A structurally complete candidate may be overclaimed] → Cap the outcome at `STRUCTURALLY_COMPLETE_REVIEW_REQUIRED`; never infer external authenticity or human acceptance.
- [Lint diagnostics may leak private metadata] → Emit only allowlisted codes/field names and run public leak scans against invalid-value fixtures.
- [Refactoring the freeze path could alter execution behavior] → Characterize existing acceptance/rejection and deterministic protocol bytes before extraction; require byte-identical after-tests and keep persistence outside the shared seam.
- [The optional JSON Schema tool may be unavailable] → Keep the core generator/linter dependency-free and treat standards-based schema validation as an optional conformance check.
- [A changed or partially generated review path cannot be repaired automatically] → Use create-once, exact-idempotent semantics and perform no namespace, content, or capability-issued metadata mutation on rejection; filesystem-managed access-time changes caused solely by descriptor reads are the only exclusion.
- [A same-EUID process can replace a pathname in a namespace-operation window] → Treat that condition as account/process-boundary compromise except for the explicit post-preflight competitor test, make the exclusive cooperative writer assumption explicit, and avoid all destructive cleanup on the review publication path.
- [A failed transaction may retain a `0700` recovery sibling] → Require the mechanical ownership proof and fixed sanitized status, block current evidence while any reserved-prefix sibling exists, and keep automatic garbage collection out of scope.
- [Atomic no-replace support varies by platform and filesystem] → Preflight the Darwin/Linux implementation and symbol before staging, use no fallback, and retain provably owned staging when a later filesystem-specific no-replace failure occurs.
- [Exact verification reads may update access time] → Exclude only filesystem-managed access-time changes caused solely by descriptor reads from the otherwise uniform ban on namespace, content, or capability-issued metadata mutation, while still requiring bounded reads and unchanged identity/content state across each member read.

## Migration Plan

1. Capture the archived S0 truth, existing protocol-render hashes, validator behavior, and protected artifact hashes.
2. Add RED tests for exact inventory parity, non-executable templates, strict schema shape, pure lint outcomes, zero source/lockbox reads, sanitized failures, and zero private/protocol mutation.
3. Extract the pure pre-freeze validation seam while proving existing freeze bytes and execution behavior are unchanged.
4. Implement deterministic pack generation and metadata-only linting, then add the bounded CLI surface. Require the trusted root, ancestors, and `reports/public-sample` parent to pre-exist and pass stable ownership/mode checks; preflight Darwin/Linux no-replace support; and reject changed, partial, unsafe, or recovery-blocked state with no namespace, content, or capability-issued metadata mutation except filesystem-managed access-time changes caused solely by descriptor reads.
5. Generate the real public bundle once through the absent-path no-replace branch and run deterministic second generation through the mechanically exact no-op branch. Verify zero reserved-prefix siblings and that neither successful run invokes exchange, `unlinkat`, `rmdir`, destructive cleanup, or an ordinary fallback before adding evidence navigation and the Chinese Human Brief; then run focused/full tests, Ruff, Mypy, strict OpenSpec, deterministic replay, leak/link scans, protected-hash checks, and independent review.
6. If any check requires a real source, actual authority evidence, human acceptance, protocol persistence, or lifecycle advancement, stop the apply as out of scope. Archive remains separately authorized.

Rollback is removal of the new review-pack module, CLI route, tests, public bundle, and additive navigation entries only after their identities are explicitly reviewed. Any retained high-entropy `0700` recovery sibling is not automatically garbage-collected; it requires separate manual disposition. The existing S0 boundary artifacts, execution capability, and legacy public-evidence writer behavior require no data migration or semantic rollback.

## Open Questions

No implementation question is silently delegated to apply. Real provider/reviewer identities, true authority evidence, the source-frame digest, numeric/statistical bindings, and human acceptance intentionally remain unavailable; resolving them requires external evidence and a later separately reviewed change rather than defaults in this phase.
