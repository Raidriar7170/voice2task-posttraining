## 1. OpenSpec Setup

- [x] 1.1 Create proposal, design, spec deltas, and tasks for `recover-step-matched-projection-inputs`.
- [x] 1.2 Validate the new OpenSpec change in strict mode before implementation.

## 2. Source Discovery and Boundary Decision

- [x] 2.1 Inspect committed step-matched artifacts, configs, manifests, split/gold sources, evaluator code, and prior blocked projection evidence.
- [x] 2.2 Search local and approved A100 run roots for original step-matched raw predictions/gold artifacts without writing or running prediction.
- [x] 2.3 Decide path A/B/C from evidence and record why older non-step-matched predictions, aggregate metrics, row summaries, and inferred predictions are not substitutes.

## 3. Test-First Recovery Guardrails

- [x] 3.1 Add failing tests for artifact discovery, adapter identity validation, sample ID alignment, gold hash validation, and duplicate/missing row detection.
- [x] 3.2 Add failing tests for metric reproduction, invalid boundary fail-closed, invalid metric fail-closed, public-safe manifests, and retention metadata.

## 4. Recovery Implementation

- [x] 4.1 Recover existing raw artifacts if found, or fail closed without prediction-only reproduction.
- [x] 4.2 Write sanitized raw-input artifacts, artifact manifest, boundary verification, metric reproduction, recovery summary, and blocked artifact when applicable.
- [x] 4.3 Add the minimal artifact-retention hook if current prediction/eval code lacks row-level retention.

## 5. Documentation and Review

- [x] 5.1 Update README.md, README_en.md, and CONTEXT.md with the recovery result and non-claims.
- [x] 5.2 Generate `docs/human-briefs/2026-06-21-recover-step-matched-projection-inputs.html`.
- [x] 5.3 Run `PYTHONPATH=src pytest -q`.
- [x] 5.4 Run `PYTHONPATH=src ruff check src tests`.
- [x] 5.5 Run `OPENSPEC_TELEMETRY=0 openspec validate --all --strict`.
- [x] 5.6 Run `git diff --check` and public leak scan.
- [x] 5.7 Run a read-only Reviewer pass, fix in-scope Must Fix items only, then stop without running Contract V2 projection, training, DPO, data expansion, or schema implementation.
