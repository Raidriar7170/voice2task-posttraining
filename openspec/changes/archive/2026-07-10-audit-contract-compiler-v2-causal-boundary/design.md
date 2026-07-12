## Context

Voice2Task currently trains and predicts the complete eight-field V1 Browser Task Contract. The audited local path uses JSON-only prompting, greedy generation, Markdown-fence suppression, post-generation strict parsing/schema validation, and at most one schema retry; it has not yet established token-level grammar/JSON-Schema constrained decoding. An internal ContractCoreV2 and V1-compatible envelope exist as offline/experimental boundaries, but their deterministic transformations can mechanically improve derived-field validity without proving that the model learned more.

The preceding repair froze three facts that constrain causal interpretation:

- future strict exact uses JSON type-strict comparison, while historical metrics remain frozen under their recorded evaluator version;
- public dev/test are `DEVELOPMENT_ONLY_SPENT`, not independent blind evidence;
- lockbox-v1 has already been consumed once and is aggregate-only, so it cannot be reused to tune or retrospectively select a compiler.

The existing 99.77% `derive_display` result is a renderer support/coverage statistic. It does not test whether rendered `normalized_command` strings equal the legacy canonical gold targets. The audit must keep these concepts separate.

## Goals / Non-Goals

**Goals:**

- Establish the actual current transformation graph and field-authority boundary from committed code and artifacts.
- Separate model-authored output quality from deterministic compiler, renderer, policy, constant, and verifier effects.
- Define causal estimands and the minimum matched evidence needed to attribute a change to the compiler or to model training.
- Classify current evidence with a fail-closed status and recommend one bounded next phase.
- Produce deterministic, public-safe, reviewable evidence without running models or changing runtime behavior.

**Non-Goals:**

- No compiler, decoder, schema, prompt, evaluator-default, verifier-enforcement, or runtime integration implementation.
- No data generation/resplit, training, prediction, lockbox reuse, A100 execution, DPO/GRPO, checkpoint/adapter release, or performance claim.
- No generic chat tuning, skill routing, GUI action policy learning, public full-corpus release, production-readiness claim, or live-browser benchmark claim.

## Decisions

### 1. Audit observed and proposed architectures separately

The report will contain two graphs:

1. **Observed current graph** derived from V1 formatting/prediction/evaluation, strict parsing, schema/semantic validation, retry, ContractCoreV2, and projection code.
2. **Candidate compiler graph** that is only a hypothesis and cannot be described as implemented.

Every graph edge will cite a repo-relative source artifact and stable symbol or artifact identity. This prevents a target architecture from being mistaken for current behavior.

### 2. Assign field authority explicitly

The candidate semantic core must explicitly include `intent`, task-specific `slots`, `risk`, and `clarification` where applicable. Each intermediate and V1 leaf will record three independent dimensions:

- `value_origin`: which model, constant, renderer, policy, or verifier supplied the value;
- `constraint_owner`: which schema/policy owns its allowed domain;
- `transform`: the deterministic or learned edge that produced it.

Primary value origins use:

- `model_authored`
- `policy_derived`
- `renderer_derived`
- `constant`
- `verifier_derived`

The matrix will cover at least `safety.allow`, `safety.reason`, every task-specific `slots.<key>` leaf, route, confirmation, normalized command, language, and version—not only top-level `safety` or `slots`. It will also identify whether a leaf participates in raw-core validity, policy self-consistency, strict V1 exact, or downstream execution gates. A verifier observation cannot silently become a model-authored value or a runtime mutation.

### 3. Separate four renderer questions

Renderer evidence will report four distinct properties:

1. **support**: the renderer returned a result;
2. **determinism**: repeated calls return the same result;
3. **legacy exact compatibility**: rendered output exactly equals the existing canonical V1 target;
4. **policy self-consistency**: the compiled contract satisfies the same declared deterministic task/policy table; this is not external semantic correctness.

Support or determinism alone cannot be called canonical compatibility. The audit may compute these properties over committed public-safe contracts, but it cannot change gold targets or re-score historical model metrics.

### 4. Define separate system and model estimands

The deterministic **system/compiler estimand** uses one frozen raw-core record as the observation unit and compares identity/preserve-legacy with candidate compilation over the same preregistered eligible population. Model outputs, data, prompt, decoding, and evaluator version must be identical. The primary outcome is ITT compiled V1 strict exact (plus separately named safety/slot guardrails) over the full fixed denominator; parse-invalid and renderer-unsupported records count as failures. A supported-only rate may be reported only as a secondary diagnostic with its smaller denominator printed next to it.

The **model-learning estimand** uses one preregistered evaluation family as the observation unit and requires matched training and prediction arms with the same data boundary, prompt, decoding, optimization budget, compiler policy, evaluator, and clean eligible evaluation set, plus predeclared multi-seed family-level aggregation and uncertainty. Compiler-filled fields cannot be counted as evidence that model parameters improved.

These estimands will never be merged into one headline delta.

### 5. Use fail-closed causal statuses

- `CAUSAL_IDENTIFICATION_SUPPORTED`: every required intervention, control, invariant, provenance, eligible evaluation, and uncertainty condition is satisfied for the named estimand.
- `CAUSAL_IDENTIFICATION_BLOCKED`: a required input or independence condition is absent or consumed.
- `DESCRIPTIVE_ONLY`: deterministic mechanism/compatibility evidence exists, but it cannot identify a causal performance effect.

Given the known spent public dev/test and consumed one-look lockbox, full compiler/model causal identification in this audit is preset to `CAUSAL_IDENTIFICATION_BLOCKED`. Renderer and transformation mechanics may be `DESCRIPTIVE_ONLY`; the current audit has no path to a positive causal status.

### 6. Bind audit output to committed evidence

A deterministic helper may read only an explicit whitelist:

- current implementation/spec files needed to verify formatting, prediction/decoding, schema/semantic policy, evaluation, ContractCoreV2, and projection symbols;
- `data/public-samples/seed_traces.jsonl` and its current manifest as the renderer source population;
- the committed public split-integrity audit, internal-core summary, and other aggregate public reports explicitly named in the audit manifest;
- for lockbox-v1 only: its manifest, final run card, base/final aggregate metrics, and final comparison.

The helper MUST NOT read `data/lockbox/lockbox-v1.jsonl`, lockbox drafts, row-level lockbox failures, raw/private predictions, private corpora, caches, adapters, or checkpoints. Its JSON output will include methodology version, whitelist paths/hashes, denied-input assertions, field-authority records, transformation edges, renderer dimensions, decoding inventory, estimand matrices, confounders, status reasons, and explicit false claim flags. Markdown and the Human Brief will be rendered from the same machine result.

### 7. Fix the renderer population and denominator

Renderer compatibility is descriptive over exactly the 247 current formal rows in `data/public-samples/seed_traces.jsonl`; one seed row is one observation. SFT augmentations, DPO pairs, model predictions, and lockbox rows are excluded. No target-level deduplication or supported-case filtering changes the ITT denominator. Parse-invalid and unsupported rows count as ITT failures; supported-only counts are secondary. Results involving current public dev/test are always `DESCRIPTIVE_ONLY` and cannot select or tune a candidate compiler.

## Risks / Trade-offs

- [Static code evidence can drift after refactors] → Bind every source to a hash and stable symbol name; fail regeneration when required symbols disappear.
- [A deterministic compiler can legitimately improve system metrics] → Report that as a system transformation effect, never as model-learning improvement.
- [Renderer exact compatibility can expose many legacy mismatches] → Preserve the negative result over the fixed 247-seed ITT population; do not retune the renderer or gold policy within the audit.
- [Current evaluation sets are ineligible for a new causal headline] → Return `DESCRIPTIVE_ONLY` or `CAUSAL_IDENTIFICATION_BLOCKED` and recommend a later preregistered evaluation-design phase.
- [An audit helper could grow into implementation] → Restrict apply to read-only derivation, reports, tests, navigation, and a Human Brief; any runtime/compiler change requires a new reviewed OpenSpec change.

## Migration Plan

1. Add RED tests for audit schema, leaf authority, decoding terminology, fixed 247-seed denominator, ITT/support separation, causal status rules, whitelist/denylist, input hashes, and scope flags.
2. Implement the deterministic read-only audit helper and generate JSON/Markdown from committed inputs.
3. Review the transformation DAG, estimands, confounders, and status decision against source code and authoritative evidence.
4. Update evidence navigation/current status and generate a Chinese Human Brief.
5. Run focused/full tests, Ruff, focused Mypy, OpenSpec strict validation, public leak scan, deterministic regeneration, truth-surface validation after archive, and diff checks.

No runtime migration or rollback is needed. The audit can be reverted as reports/tests/docs without touching models, datasets, predictions, or historical metrics.

## Open Questions

None for the proposal-only opening. Apply must answer the evidence classification and recommend—not execute—the next bounded phase.
