## Design

This change follows the repository's existing public-safe A100 pattern:

1. Committed config templates contain only public IDs and placeholders such as
   `<a100_project_root>`.
2. A private remote override resolves the A100 project root, base-model path,
   and adapter path outside git.
3. The prediction command writes sanitized public-sample predictions and sidecars
   for one split at a time.
4. The committed evidence pack imports only predictions, split gold rows,
   metrics, metadata, prompt snapshots, sanitized raw decoded summaries,
   generation traces, diagnostics, and public-safe summary manifests.

The tiny adapter itself remains private. This phase reuses it as an instrument
for diagnosis rather than as a releasable artifact.

## Evidence Interpretation

The combined manifest compares:

- prior train-internal tiny-overfit metrics from
  `reports/public-sample/current-manifest-tiny-overfit-probe/`
- new current-manifest `dev` and `test` prediction metrics

The comparison is diagnostic only. It may show no held-out recovery, partial
held-out recovery, or a stronger signal, but it still cannot prove
private-corpus generalization, production readiness, or live-browser benchmark
improvement.

## Safety Boundary

Public artifacts must not contain raw logs, checkpoints, adapters, private
overrides, private paths, host details, SSH details, tokens, private corpus rows,
or local absolute paths. Leak scans are required before archive and commit.
