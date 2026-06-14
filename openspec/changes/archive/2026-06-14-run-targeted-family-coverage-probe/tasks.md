## 1. Local Contract and Configs

- [x] 1.1 Add focused tests for `train_source_ids` SFT row selection metadata.
- [x] 1.2 Add targeted family coverage A100 SFT and train/dev/test prediction config templates.
- [x] 1.3 Add config tests proving 7B model use, public-safe placeholders, exact train source IDs, and split-specific predictions.

## 2. A100 Execution

- [x] 2.1 Prepare a private remote override under the approved private A100 project root without committing private paths.
- [x] 2.2 Run read-only A100 preflight, choose a safe idle GPU, and launch targeted SFT training only if placement is safe.
- [x] 2.3 Run targeted adapter prediction for train, dev, and test splits with sanitized sidecars.

## 3. Evidence Import and Reporting

- [x] 3.1 Import sanitized public-safe train/dev/test predictions, metrics, schema/alignment/decoding diagnostics, prompt snapshots, raw decoded summaries, generation traces, and metadata.
- [x] 3.2 Generate targeted probe manifest and report comparing current tiny held-out baseline and prior broad residual repair evidence.
- [x] 3.3 Generate a concise Chinese Human Brief with project-stage progress and non-claim boundaries.

## 4. Validation and Closeout

- [x] 4.1 Run focused pytest, OpenSpec validation, leak scans, and `git diff --check`.
- [x] 4.2 Run a reviewer pass over the diff and fix Must Fix items in scope.
- [x] 4.3 Archive the change if complete and apply guarded auto integration.
