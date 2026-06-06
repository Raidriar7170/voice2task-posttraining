## 1. Trace Field Tests

- [x] 1.1 Add focused tests that fail until generation trace rows expose max-token-hit status, finish-state basis, stop-boundary evidence, and actual-stop-reason-recorded status.
- [x] 1.2 Verify the new tests fail for the expected missing-field reason before production code changes.

## 2. Instrumentation

- [x] 2.1 Update the trained-adapter generation trace row builder to add the stop-boundary evidence fields while preserving existing trace keys and values.
- [x] 2.2 Verify raw and retry attempt sidecars still preserve attempt ordering, token counts, EOS visibility, finish state, and public-safety scan behavior.

## 3. Evidence And Brief

- [x] 3.1 Publish a public-safe local evidence pack documenting the new trace fields, source diagnosis link, non-claim boundaries, and leak-scan result.
- [x] 3.2 Generate a concise Chinese Human Brief for this OpenSpec phase.

## 4. Validation And Closeout

- [x] 4.1 Run focused tests, full test suite, lint/type checks, dataset validation, DPO pair checks, public-leak scans, `git diff --check`, and `openspec validate --all --strict`.
- [x] 4.2 Review the diff, fix Must Fix findings, archive the OpenSpec change, rerun validation, and commit the completed phase.
