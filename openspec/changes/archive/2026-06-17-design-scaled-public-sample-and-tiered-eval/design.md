## Context

The latest model evidence for `public-sample-20260617T045941Z` is the current-123 A100 SFT retry. It keeps JSON validity at `1.0` and safety recall at `1.0`, but strict full-contract exact remains low (`0.4348` dev / `0.3768` test) and strict slot F1 remains partial (`0.5580` dev / `0.5459` test). Earlier narrow repair phases improved specific risks but introduced trade-offs, especially around confirmation and exact matching.

The current public sample is still small: 102 seeds, 261 SFT rows, 881 DPO pairs, and only 123 train rows. Before another SFT retry, the project needs a reviewable plan for larger family-balanced data and diagnostic tiered evaluation.

## Goals / Non-Goals

**Goals:**

- Produce a public-safe, design-only scale-up plan that targets a larger formal public sample without immediately mutating seed, SFT, DPO, or manifest files.
- Identify target family balance, augmentation depth, accepted contract shape coverage, and rejected/hard-negative coverage needed before the next materialization phase.
- Define tiered evaluation diagnostics that explain where strict exact fails without replacing strict exact metrics.
- Update status surfaces and generate a concise Human Brief for the decision.

**Non-Goals:**

- No seed materialization, public sample rebuild, SFT/DPO/GRPO run, prompt change, evaluator relaxation, slot normalization, prediction repair, checkpoint/adapter release, private-corpus publication, production-readiness claim, or live-browser benchmark claim.
- No generic chat fine-tuning, skill routing, GUI action policy learning, or first-phase GRPO.

## Decisions

1. **Design before materialization.** The next phase should create a scale-up design artifact first. A later phase can materialize reviewed candidate seeds if the design is accepted by local validation and review.

2. **Target breadth over another narrow retry.** The design should move from point repairs to family-balanced coverage. A reasonable planning target is around 240 seeds, but this phase should record it as a target distribution, not as committed generated data.

3. **Keep strict metrics authoritative.** Tiered evaluation should split errors into structural validity, task/route, safety/confirmation, slot, and full exact tiers. It must not make `slot_f1_soft`, semantic similarity, or partial structural correctness a public success metric.

4. **Use existing public evidence as inputs.** The design should derive from `CONTEXT.md`, `reports/final_status.md`, current-123 retry metrics, residual/failure slices, current public-sample manifest counts, and historical diagnosis artifacts. It should not require remote A100 work.

5. **Preserve public/private boundaries.** The design artifact can include aggregate counts, family names, sanitized row ids, and target shape sketches. It must not include private paths, raw private rows, raw logs, checkpoints, adapters, SSH details, or tokens.

## Risks / Trade-offs

- **Risk: over-planning instead of improving data.** Mitigation: keep the design bounded to one report with explicit next materialization tasks.
- **Risk: tiered metrics get mistaken for relaxed success.** Mitigation: every artifact must state that strict `contract_exact_match` and strict `slot_f1` remain headline metrics.
- **Risk: 240 seeds is still small for 7B LoRA.** Mitigation: frame it as the next public-sample milestone, not proof that recovery will follow.
- **Risk: family balance hides rare but critical safety cases.** Mitigation: require separate safety and confirmation target coverage, not only task-family counts.
