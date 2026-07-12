## Context

The archived `preregister-clean-matched-compiler-and-model-evidence-design` phase defines one future acquisition, two family-disjoint one-look partitions, separate compiler/system and model-learning estimands, and a six-state readiness lifecycle. It deliberately stops at `DESIGN_ONLY`: all 29 execution bindings remain `UNBOUND_BY_DESIGN`, no acquisition source or family registry exists, the protocol is not frozen, and both causal-identification statuses are blocked.

The repository contains spent public train/dev/test evidence and a consumed lockbox-v1 one-look boundary. Neither may seed, substitute for, or validate the new population at row level. There is currently no independent clean acquisition frame in the repository. This change must therefore be executable as a conditional materialization: it may reach `POPULATION_MATERIALIZED_AND_SEALED` only when an externally authorized metadata-only source frame and every binding are verifiable; otherwise it must publish a bounded blocked result without fabricating data or weakening the design.

The materialization is a real private data mutation, but it is not evaluation-row creation. It creates only family/provenance/stratum metadata and partition membership under a gitignored private root. Public artifacts contain aggregate counts, root hashes, protocol identities, state transitions, and rejection codes—not rows, family/member identifiers, per-item hashes, private paths, gold, predictions, or outcomes.

## Goals / Non-Goals

**Goals:**

- Validate an exact typed dossier for all 29 canonical bindings and reject every placeholder, alias, null, conflicting value, unreviewed source, or unhashed derivation.
- Freeze one canonical protocol digest before family-registry or partition-membership creation.
- Accept only an explicitly supplied, regular-file, no-symlink, metadata-only acquisition frame with an independently reviewed source/ancestry attestation.
- Deterministically create a private family registry, assign every eligible family exactly once to `compiler_system_evaluation` or `model_learning_evaluation`, and atomically seal both partitions.
- Preserve zero one-look access and publish public-safe success or blocked evidence with replayable aggregate verification.
- Advance monotonically only through `DESIGN_ONLY`, `EXPERIMENT_BINDINGS_COMPLETE`, `PROTOCOL_FROZEN`, and at most `POPULATION_MATERIALIZED_AND_SEALED`.

**Non-Goals:**

- No evaluation row text, audio, ASR transcript, annotation, gold contract, prediction, metric, outcome, adapter, checkpoint, compiler artifact, or model artifact is created or opened.
- No compiler/decoder implementation, prompt/decoding/schema/evaluator/runtime change, training, prediction, A100 execution, one-look execution, arm-artifact freeze, or post-result tuning.
- No public-sample, remediation, challenge, prediction, or lockbox-v1 row may be used as the acquisition source; the materializer may not read lockbox rows.
- No generic chat fine-tuning, skill routing, GUI action-policy learning, first-phase GRPO, full local corpus publication, checkpoint release, or live-browser/model/executable/production/safety improvement claim.
- No automatic proposal, apply, archive, compiler pilot, or model-learning experiment after this change.

## Decisions

### 1. Add a separate operational capability

This change adds `clean-compiler-model-evaluation-boundary` rather than modifying the archived `clean-matched-causal-evidence-design` capability. The archived capability remains the historical design contract and source of the exact 29-field inventory, estimands, lifecycle, and hard boundaries. The new capability operationalizes only binding, freezing, metadata-only materialization, and sealing.

Alternative considered: modify the design-only capability in place. Rejected because it would mix a historical no-data truth surface with a later phase that intentionally creates private registry and membership artifacts.

### 2. Treat the source as an external metadata-only sampling-frame contract

The exact `acquisition_source` remains an apply-time binding; this design does not pretend the source already exists. An acceptable source contract is an independently authorized blind family-level sampling frame whose provider attests that its ancestry excludes current public train/dev/test, remediation, challenge, prediction, and lockbox-v1 row content. Provider and reviewer/approval identities are separate, the contract declares the permitted task brief/schema, and it explicitly denies a natural-ASR claim.

The single canonical private root is `data/local-private/clean-compiler-model-evaluation-boundary-v1/`; the single public root is `reports/public-sample/clean-compiler-model-evaluation-boundary-v1/`. Each source-frame record represents exactly one semantic-family candidate, so its source family key must be unique in the frame. It may contain only an opaque stable ASCII family candidate id, source batch id, source family key, frozen stratum, eligibility state, coarse provenance class, ancestry-attestation digest, and unit hash. The schema rejects input text, audio, transcript, gold, target contract, prediction, metric, outcome, free-form notes, and private path fields.

The CLI accepts explicit files only and opens them relative to an already opened trusted private-root directory descriptor. It validates each component with `openat`-style descriptor-relative opens, uses `O_NOFOLLOW` on the final open, verifies the opened identity with `fstat`, requires a regular file with `st_nlink=1`, applies frozen byte/record limits, and reads the same opened descriptor exactly once so hashing and schema validation share one immutable bytes snapshot. Parent replacement, exchanged symlinks, hardlinks to public/lockbox files, identity drift, globbing, and broad directory discovery are rejected before payload use. Public-sample, lockbox, report, cache, adapter, checkpoint, and log paths remain exact/prefix denied as an additional policy layer.

Source-frame JSONL is strict UTF-8 without BOM. Duplicate JSON keys, unknown fields, non-finite numbers, invalid UTF-8, and extra trailing content are rejected. Opaque ids use the frozen ASCII grammar `[A-Za-z0-9._:-]{1,128}`. Canonical records use sorted keys, no insignificant whitespace, `\n` record termination, integers or canonical decimal strings rather than binary floats, and a frozen UTF-8 JSON escaping policy. `unit_hash` is computed over the canonical record with `unit_hash` removed. Registry and membership roots sort records by their frozen opaque id and use versioned domain-separated, length-delimited SHA-256 inputs; the partition score likewise length-prefixes the domain, seed, stratum, and family id rather than concatenating ambiguous strings.

Alternative considered: derive a frame from existing public or lockbox data. Rejected because those evidence surfaces are spent and would invalidate independence.

### 3. Represent each canonical binding as a typed, source-hashed dossier

The protocol contains exactly the existing 29 keys grouped as:

- source: 2;
- partition mechanics: 7;
- compiler/model arm identities and paired seeds: 5;
- effect, power, dependence, interval, guardrail, and stop-rule analysis: 15.

Each binding records a concrete value, value type/unit, public-safe authority label, authority/source hash, derivation method and input hashes when derived, applicability statement, no-clean-row/gold/outcome/lockbox-row-access attestation, and review verdict. `UNBOUND_BY_DESIGN`, `UNBOUND`, `TBD`, `UNKNOWN`, null, blocked sentinels, private paths, duplicate aliases, or conflicting artifact-local copies do not count as values. All 29 must be `BOUND` before `EXPERIMENT_BINDINGS_COMPLETE` is reached.

Arm bindings identify immutable protocol definitions, not executable artifacts. A bound compiler intervention or training recipe does not advance `arm_artifacts_status`; model arms still require exactly one intervention and an identical paired-seed list with at least three seeds, while the power contract may require more than three.

Alternative considered: bind only the nine acquisition/partition fields before materialization. Rejected because the committed lifecycle requires all 29 before protocol freeze, and late arm/statistical choices would permit outcome-dependent redesign.

### 4. Freeze statistical assumptions without inventing clean-data estimates

Historical aggregate-only evidence may constrain metric ranges, base-rate sensitivity, and stress scenarios. It may not be used as a point estimate for clean-family ICC, paired compiler discordance/covariance, paired-seed correlation, or seed failure/attrition.

Each compiler/model card chooses exactly one planning mode before clean outcomes exist:

- `EFFECT_TARGETED`: freeze a practically meaningful MDE, then compute the required family capacity;
- `CAPACITY_CONSTRAINED`: freeze independently available source capacity, then compute achievable MDE.

The same card may not optimize both. Unsupported point estimates are replaced by a finite, sourced conservative sensitivity grid or worst-case bound; if no defensible grid exists, the binding remains incomplete and materialization blocks. Compiler planning preserves paired-record contrasts and family clustering. Model planning preserves family-by-paired-seed hierarchy, all-assigned-seed ITT failure coding, paired-seed dependence, and seed-superpopulation limitations. Clean outcomes never resize, top up, repartition, select, or tune the population.

This v1 chooses exact-capacity semantics rather than down-selection. The metadata frame must contain exactly `target_total_family_count` eligible, unique family candidates. `target_partition_allocation` is a frozen integer quota matrix indexed by stratum and the two partition ids; every cell is nonnegative, its row/column/overall sums are validated, and its overall sum equals `target_total_family_count`. Shortfall and oversupply both block. There is no inclusion seed, candidate deletion, or second-stage selection algorithm.

### 5. Freeze one canonical protocol before materialization

Before freeze, the process validates only the independently reviewed source contract/attestation and its declared expected frame digest; it must not open the source-frame payload. The canonical protocol serializes the 29 binding dossiers, source contract and declared expected frame hash, frame schema/version, exact integer quota matrix, partition algorithm, lifecycle version, both preregistration cards, invariant matrix, hard stops, privacy policy, and public/private artifact schemas. Canonical JSON follows the strict encoding above, rejects duplicate/unknown keys and non-finite numbers, and produces one `protocol_sha256`; a double render must be byte-identical.

The partition seed is non-selectable: it is independently precommitted or deterministically derived through a versioned, domain-separated rule from the protocol id and the source contract's declared expected frame digest. Freeze time is either a pre-bound value excluded from reproducibility hashes or omitted; runtime wall-clock values never affect deterministic bytes. After freeze, no binding, expected source hash, schema, seed, quota, minimum, or stop rule may change in place. Any change requires a new protocol version and a separately reviewed change before registry creation.

Only after `PROTOCOL_FROZEN` may the source-frame payload be opened for the first time. Its actual one-snapshot digest must equal the expected digest frozen in the protocol before any record is decoded or any registry artifact is staged. This chronology preserves the prior rule that partition mechanics are frozen before acquisition/materialization begins.

### 6. Materialize a metadata-only registry, then assign exactly once

After protocol freeze, the materializer performs the first payload open, reads the bounded source bytes once from the verified descriptor, rechecks the frozen hash before decoding, and stages a private family registry. It validates one unique family candidate per record, allowed provenance/strata values, source eligibility, ancestry attestation, strict canonical hashes, and semantic-family uniqueness. A frame containing forbidden row/gold/outcome fields is marked compromised and cannot be corrected and retried under the same source contract or expected digest.

Lineage checks available at this stage cover source/provenance ancestry and semantic-family overlap. Exact, normalized, and template row-level disjointness remain explicitly `PENDING_ROW_AUTHORING_GATE` because no row text exists; they must not be reported as passed. Lockbox overlap is accepted only through a `SEALED_AGGREGATE_ATTESTATION_ONLY` containing the protocol hash, expected/actual source-frame root, family-registry root, public lockbox manifest hash, validator implementation/version hash, separately authorized validator and reviewer approval identities/digests, comparison-category aggregate counts, `row_level_output_count=0`, and an attestation digest or signature. Missing/unauthorized identities, digest drift, nonzero overlap, or any row-level output blocks. The materializer never imports or reads lockbox rows or member hashes.

Partition assignment uses the frozen `sha256-partition-by-stratum-v1`: within each frozen stratum, a versioned domain-separated, length-prefixed hash of the seed, stratum, and canonical family id determines order, then the exact frozen integer quota matrix determines membership. The eligible family count must equal the frozen target exactly. Python RNG state, filesystem order, retries with alternate seeds, post-hoc balancing, down-selection, top-ups, and manual reassignment are forbidden.

Both partitions are promoted atomically only after family overlap is zero, every family has exactly one membership, exact target/minimum/quota gates pass, root hashes reproduce, public/private schema separation passes, and both one-look states are zero-access. All canonical private artifacts are written and flushed inside one new staging generation directory under the canonical private parent; files and directory metadata are synced, staging and final are verified to share one filesystem, and one directory rename publishes the immutable generation. An existing final generation is never overwritten, and every seal reference is relative to files inside that generation. Failed attempts may emit a public aggregate blocker but may not expose a partially canonical registry, membership, or seal.

### 7. Publish root hashes and aggregates, never membership

Private canonical artifacts stay only under `data/local-private/clean-compiler-model-evaluation-boundary-v1/` and may include the source attestation, source frame, family registry, partition membership, binding review, and private seal. Apply verification uses ignore checks, tracked-file listings, status, and committed-diff scans to prove that the root is ignored and no private artifact is tracked. No private path is recorded in public evidence.

Public output only under `reports/public-sample/clean-compiler-model-evaluation-boundary-v1/` contains a deterministic summary, protocol manifest, population-seal attestation, and lineage attestation. It may report one versioned domain-separated root hash for each private artifact class, total/partition/stratum counts, provenance-category counts, violation counts, lifecycle states, blocked reasons, and false execution/claim flags. A hash that is unavailable on a blocked path is represented by the explicit state `NOT_AVAILABLE`, never null, empty text, or a fabricated digest. Public output may not contain opaque member ids, per-member hashes, membership lists, row content, or low-entropy values that enable enumeration.

The machine report uses the phase-specific internal `evidence_status` below. Evidence-index classification continues to use the existing allowed vocabulary: `CURRENT` only for a successful sealed boundary and `BLOCKED` for a blocked phase. This change does not silently widen the evidence-index status enum.

### 8. Use monotonic, atomic readiness states and honest terminal truth

Success advances in order to a maximum state of `POPULATION_MATERIALIZED_AND_SEALED` with:

- `evidence_status=EVALUATION_BOUNDARY_MATERIALIZED`;
- `decision=POPULATION_BOUNDARY_READY_ARM_ARTIFACTS_BLOCKED`;
- `execution_bindings_status=COMPLETE`;
- `protocol_freeze_status=FROZEN`;
- `clean_population_status=MATERIALIZED_AND_SEALED` with `population_unit=SEMANTIC_FAMILY_METADATA_ONLY`;
- `clean_evaluation_rows_status=NOT_CREATED` and row-level disjointness `PENDING_ROW_AUTHORING_GATE`;
- both partition one-look states `SEALED_NOT_ELIGIBLE`, `access_count=0`, and `consumed=false`;
- `arm_artifacts_status=NOT_FROZEN`, `experiment_preregistration_status=NOT_EXECUTABLE`, and `execution_readiness=false`;
- both causal-identification statuses `CAUSAL_IDENTIFICATION_BLOCKED`;
- `clean_independent_evidence_claim=false`, `row_clean_claim=false`, and `evaluated_benchmark_claim=false`.

Truthful mutation flags are `boundary_materialization=true`, `private_family_registry_created=true`, and `private_partition_membership_created=true`; `public_data_mutation`, `formal_training_data_mutation`, `lockbox_mutation`, `clean_evaluation_row_creation`, `gold_access`, `outcome_access`, `prediction_run`, `training_run`, `a100_execution`, `experiment_execution`, and one-look access remain false.

On failure, `evidence_status=BLOCKED`, `decision=CLEAN_EVALUATION_BOUNDARY_MATERIALIZATION_BLOCKED`, `execution_readiness=false`, both causal-identification statuses remain blocked, and every performance/readiness claim remains false. The exact blocked matrix prevents successful fields from leaking into negative evidence:

| Path | current state | bindings | protocol | population / canonical artifacts | partitions / one-look | integrity and reuse |
| --- | --- | --- | --- | --- | --- | --- |
| S0 source/binding block | `DESIGN_ONLY` | `INCOMPLETE` | `NOT_FROZEN` | `NOT_MATERIALIZED`; registry/membership/seal created=false | both `NOT_MATERIALIZED`; one-look `NOT_AVAILABLE`, access=0, consumed=false | `NOT_CREATED`; boundary reuse=false; a reviewed retry may supply missing pre-freeze inputs |
| S1 freeze block | `EXPERIMENT_BINDINGS_COMPLETE` | `COMPLETE` | `NOT_FROZEN` | `NOT_MATERIALIZED`; registry/membership/seal created=false | both `NOT_MATERIALIZED`; one-look `NOT_AVAILABLE`, access=0, consumed=false | `NOT_CREATED`; boundary reuse=false; a new protocol version/review is required |
| S2 materialization/seal block | `PROTOCOL_FROZEN` | `COMPLETE` | `FROZEN` | `NOT_MATERIALIZED`; canonical registry/membership/seal created=false | both `NOT_MATERIALIZED`; one-look `NOT_AVAILABLE`, access=0, consumed=false | `INTACT_BLOCKED`; boundary reuse=false; a new protocol/acquisition is required |
| Compromised at any state | last fully verified state plus observed breach | actual observed value | actual observed value | artifact-created/seal fields reflect observed facts, never success defaults | one-look state/count/consumed reflect observed access rather than forced zero | `COMPROMISED`; boundary reuse=false; new independent acquisition required |

Unavailable hashes on blocked paths are `NOT_AVAILABLE`. Early row/gold/outcome access, forbidden-field frame content, one-look access, public membership leakage, or sealed drift marks the boundary compromised and requires a new independent acquisition rather than correction, repair, or retry under the same frame digest.

Machine-readable hard stops include source unavailable/unverifiable, binding incomplete/placeholder, unsupported power assumptions, protocol hash drift, early row/gold/outcome access, lineage or lockbox-attestation failure, invalid/duplicate family registry, insufficient family/stratum capacity, nondeterministic or overlapping assignment, sealed-artifact drift, membership leakage, and one-look/experiment scope breach.

## Risks / Trade-offs

- [No independent source exists yet, so apply may end blocked] → Treat `ACQUISITION_SOURCE_UNAVAILABLE_OR_UNVERIFIABLE` as an honest terminal result and create no substitute data.
- [Metadata-only families cannot prove row-level exact/normalized/template disjointness] → Publish those checks as `PENDING_ROW_AUTHORING_GATE`; never call the population row-clean or natural ASR evidence.
- [Historical aggregates cannot identify clean dependence parameters] → Require sourced conservative grids/worst-case bounds or block rather than inventing ICC/correlation/attrition values.
- [A protocol binding may be confused with a frozen executable arm] → Keep arm protocol identity separate from `arm_artifacts_status=NOT_FROZEN`.
- [Seed or quota shopping can alter partition composition] → Use one named deterministic assignment and prohibit retries, alternate seeds, top-ups, and rebalancing.
- [Root or per-member hashes can leak a low-entropy membership set] → Publish only aggregate root hashes and counts; keep member ids and hash lists private.
- [Partial writes can be mistaken for a sealed population] → Stage privately and atomically promote only after every validation and seal check passes.
- [Lockbox overlap validation can create a second look] → Consume only an independently produced sealed aggregate attestation; the materializer never reads lockbox rows.
- [The word materialized may be mistaken for evaluation readiness] → Print `clean_evaluation_rows_status=NOT_CREATED`, `ARM_ARTIFACTS_FROZEN=false`, `ELIGIBLE_FOR_ONE_LOOK=false`, and `execution_readiness=false` together on every truth surface.

## Migration Plan

1. Add RED tests for exact typed bindings, blocked sentinels, private source policy, statistical planning modes, freeze chronology, state transitions, terminal truth, and public/private schemas.
2. Implement binding/source validators and deterministic protocol rendering without reading or creating family artifacts.
3. If the source and all bindings validate, freeze the protocol; otherwise publish the bounded blocked evidence and stop.
4. Materialize the private metadata-only family registry, validate lineage and the sealed aggregate lockbox attestation, then run deterministic exactly-once partition assignment in private staging.
5. Atomically promote private registry/membership/seal only after capacity, overlap, determinism, privacy, and root-hash gates pass.
6. Generate aggregate-only public evidence, update navigation/status, and produce the Chinese Human Brief without exposing private paths or membership.
7. Run focused/full tests, strict OpenSpec, deterministic replay, protected-hash comparisons, leak/link checks, and independent spec/code reviews. Archive remains a separate user-authorized step.

Rollback before private promotion removes only staged private files and public blocker output. Rollback after a successful seal must not mutate or silently regenerate the sealed boundary; invalidate it with a public-safe tombstone and require a new protocol/acquisition change.

## Open Questions

No design question is silently deferred. The exact acquisition source and all numeric/identity bindings are intentionally apply-time inputs because no truthful values exist in the repository today. Their absence or failed review produces a bounded result; it does not authorize defaults, synthetic substitution, public/lockbox reuse, or scope expansion.
