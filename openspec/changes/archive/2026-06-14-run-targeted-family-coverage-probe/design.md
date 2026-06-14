## Context

The archived `diagnose-heldout-family-strategy` change showed that current dev/test failures are concentrated in four held-out residual families:

- `seed-open-example` -> train analog `seed-open-help`
- `seed-clarify-ambiguous` -> train analog `seed-clarify-target`
- `seed-form-email` -> train analog `seed-form-nickname`
- `seed-block-purchase` -> train analog `seed-block-transfer`

The current tiny-overfit adapter trained only the `seed-search-weather` source family. An older public held-out residual repair run trained on the broader train split and still failed dev/test, with train exact only `1/3`. This phase tests a narrower question: can the 7B path memorize and transfer after the training subset is explicitly constrained to the four train analog families?

## Goals / Non-Goals

**Goals:**

- Add a config-level `train_source_ids` selection contract for SFT training.
- Create public-safe A100 templates for the targeted family coverage probe.
- Run the targeted 7B SFT probe and train/dev/test prediction if A100 placement is safe.
- Commit only sanitized predictions, metrics, sidecars, manifest, report, leak scans, and Human Brief.
- Compare results against current tiny held-out prediction and the older broad residual repair evidence.

**Non-Goals:**

- No new public seed rows, SFT rows, DPO rows, or public manifest changes.
- No DPO, GRPO, reward modeling, generic chat fine-tuning, skill routing, or GUI action policy.
- No prompt-policy, decoder, parser, or evaluator metric relaxation.
- No checkpoint or adapter release.
- No full private-corpus or live-browser benchmark claim.

## Decisions

1. Use `train_source_ids` rather than `max_train_rows`.
   - Rationale: row limits depend on dataset order and cannot prove the intended family coverage.
   - Alternative considered: reuse the older residual repair config. Rejected because it trained the broad train split and already produced negative evidence.

2. Keep prediction splits explicit: train, dev, and test.
   - Rationale: train prediction checks whether the targeted subset was learnable at all; dev/test remain the primary held-out evidence.
   - Alternative considered: run only dev/test. Rejected because a dev/test failure without train memorization would not distinguish learning failure from generalization failure.

3. Treat any improvement as diagnostic evidence, not release evidence.
   - Rationale: this is a public-sample probe with a private A100 adapter; it cannot support checkpoint release, private-corpus generalization, production readiness, or live-browser benchmark claims.

4. Preserve public/private boundaries.
   - Rationale: configs in git must keep `<a100_project_root>` placeholders; private overrides, raw logs, adapters, checkpoints, caches, host details, SSH details, and private paths stay off-repo.

## Risks / Trade-offs

- [Risk] The 12-row targeted subset may overfit but not transfer to dev/test. -> Mitigation: report train and held-out metrics separately and keep strict non-claim boundaries.
- [Risk] A100 is reachable but no GPU is safely idle. -> Mitigation: write blocked preflight evidence and stop the execution part without fabricating results.
- [Risk] Source-family selection hides broader train performance. -> Mitigation: compare against prior broad residual repair evidence and record exact selected row IDs.
- [Risk] Public evidence accidentally leaks remote paths. -> Mitigation: run leak scans over configs, reports, Human Briefs, and OpenSpec artifacts before commit.
