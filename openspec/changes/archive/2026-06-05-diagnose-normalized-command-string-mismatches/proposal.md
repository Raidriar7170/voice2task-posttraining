## Why

The archived confirmation-rerun row-mismatch diagnosis shows `normalized_command` mismatches on all three train-split rows, including one row where the only remaining strict exact-match failure is a string difference. Before changing prompts, training targets, decoding, or evaluator metrics, the project needs a public-safe diagnosis that isolates this strict string-field issue from schema and semantic route/task failures.

## What Changes

- Publish a local, evidence-only normalized-command string-mismatch diagnosis derived from the committed row-mismatch evidence.
- Report the three `normalized_command` mismatches and distinguish:
  - strict string-only exact-match mismatch,
  - mismatch co-occurring with schema required-field failure,
  - mismatch co-occurring with task/route/safety semantic mismatch.
- Preserve all source predictions and strict evaluator metrics without normalization, coercion, repair, semantic-equivalence scoring, or re-scoring.
- Generate a concise Chinese Human Brief and leak-scanned public evidence pack.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `contract-evaluation`: add public-safe normalized-command string-mismatch diagnosis evidence for the confirmation-required train-split rerun.

## Impact

- Affected code: small diagnostic helper and report writer in `src/voice2task/evaluation.py` and `src/voice2task/reports.py`.
- Affected tests: focused report/helper test and evidence-pack boundary test.
- Affected evidence: new public-safe report directory under `reports/public-sample/confirmation-rerun-normalized-command-string-mismatch-diagnosis/`.
- No A100 execution, training, prediction rerun, prompt change, decoder change, parser change, schema change, evaluator metric change, checkpoint/adapter publication, or dependency change.
