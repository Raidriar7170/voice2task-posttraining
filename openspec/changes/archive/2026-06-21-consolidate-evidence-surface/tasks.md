## 1. Evidence Baseline

- [x] 1.1 Verify latest Contract V2 projection summary and formal manifest paths, counts, and current metrics.
- [x] 1.2 Classify key public-sample report directories and active OpenSpec changes as current, historical, superseded, blocked, design-only, raw-input, or archived.

## 2. Evidence Index And Checks

- [x] 2.1 Add failing pytest coverage for the evidence surface consistency contract.
- [x] 2.2 Add `reports/public-sample/evidence-index.json` and `reports/public-sample/EVIDENCE_INDEX.md`.
- [x] 2.3 Implement `scripts/check_current_truth_surface.py` to validate current docs, index paths/statuses, manifest counts, latest summary metrics, active OpenSpec count, and public leak safety.
- [x] 2.4 Make the focused evidence-surface pytest pass.

## 3. Current Truth Documents

- [x] 3.1 Rewrite README.md as the external reviewer current snapshot with current evidence links and claim boundaries.
- [x] 3.2 Rewrite README_en.md with the same current snapshot and boundaries in English.
- [x] 3.3 Rewrite CONTEXT.md as the compact developer/Codex current truth surface with the required eight sections.

## 4. OpenSpec Cleanup

- [x] 4.1 Archive completed OpenSpec changes that are already pushed and no longer active work.
- [x] 4.2 Archive blocked-then-recovered or superseded OpenSpec changes while preserving their blocked/superseded conclusions.
- [x] 4.3 Verify active OpenSpec changes are zero and no active changes conflict with the current truth.

## 5. Closeout

- [x] 5.1 Add a concise Chinese Human Brief for `consolidate-evidence-surface`.
- [x] 5.2 Run required validation: `PYTHONPATH=src pytest -q`, `PYTHONPATH=src ruff check src tests`, `OPENSPEC_TELEMETRY=0 openspec validate --all --strict`, `python scripts/check_current_truth_surface.py`, `git diff --check`, and a public leak scan.
- [x] 5.3 Archive `consolidate-evidence-surface` after validation if appropriate, then rerun final OpenSpec/current-truth checks.
