## Context

The latest A100 fence-suppression rerun produced strict schema-valid train-row predictions but left one strict exact-match residual: `seed-search-weather-aug-1` emitted `slots={"city":"北京","date":"明天","topic":""}` while the gold target requires compact `slots={"query":"北京明天天气"}`. The repository already has compact query prompt guidance and public sample SFT targets, so this phase should not duplicate old policy. The remaining local lever is to make the decomposed slot shape an explicit rejected preference example and to strengthen model-visible guidance around that exact rejected shape.

## Goals / Non-Goals

**Goals:**

- Add a public-safe DPO hard negative that rejects decomposed `city/date/topic` slots for public-readonly search/weather contracts.
- Strengthen shared SFT/prediction prompt wording so the rejected decomposed shape is visible as a wrong slot target, while preserving the compact `slots.query` target.
- Generate public-safe evidence, tests, and a Human Brief that distinguish local policy/data reinforcement from model recovery.

**Non-Goals:**

- No A100 execution, SFT/DPO training, prediction rerun, parser relaxation, evaluator metric change, slot normalization, semantic-equivalence scoring, prediction repair, re-score, checkpoint release, adapter release, production-readiness claim, held-out generalization claim, live-browser benchmark claim, or broad model-quality improvement claim.

## Decisions

1. Add a new hard-negative category instead of changing evaluator semantics.

   The residual is a strict output-shape failure. Marking `city/date/topic` as equivalent would weaken the contract boundary; a DPO rejected example keeps the scoring semantics strict while making the undesirable shape explicit in training data.

2. Limit the public data change to applicable search/weather contracts.

   The decomposed-slot rejected shape only makes sense when the chosen contract is a public-readonly `search_web` contract with compact `slots.query`. Other task types should keep their existing hard-negative set.

3. Keep prompt guidance generic and non-gold.

   The prompt may show a generic wrong slot-shape example, but prediction prompts must still not include row-specific gold target contracts or target-only slot strings.

4. Treat this as local readiness evidence.

   The phase proves only that the current repo emits the desired local prompt/data policy and public-safe evidence. A later A100 prediction-only rerun is required before claiming any trained-adapter behavior change.

## Risks / Trade-offs

- [Risk] Increasing public DPO pair count breaks stale tests or briefs that hardcode 26 pairs. -> Update current tests and generated public data; do not rewrite historical briefs.
- [Risk] The new prompt wording leaks row-specific gold values. -> Use generic examples and assert prediction prompts do not include target-only strings.
- [Risk] The evidence is overstated as model recovery. -> Include explicit non-claims in manifest, report, Human Brief, and tests.
