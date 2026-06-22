## 1. Boundary And Tests

- [x] 1.1 Confirm required authoritative evidence exists and source boundaries are valid.
- [x] 1.2 Add focused failing tests for Hybrid Slot Representation V1 field ownership, representation matrix determinism, source-span semantics, projection metrics, and claim boundaries.

## 2. Design Projection

- [x] 2.1 Implement a read-only design/feasibility analysis script without modifying schemas, evaluators, predictions, gold contracts, or training targets.
- [x] 2.2 Generate `reports/public-sample/hybrid-slot-representation-v1/summary.md`, `summary.json`, `representation-matrix.json`, `feasibility-projection.json`, and `recommended-next-change.md`.
- [x] 2.3 Generate `docs/hybrid-slot-representation-v1.md` with the architecture, field ownership, source-span semantics, matrix summary, feasibility results, vertical-slice decision, risks, claim boundaries, and non-goals.

## 3. Truth Surface And Archive

- [x] 3.1 Add concise updates to `CONTEXT.md`, `README.md`, `README_en.md`, `reports/public-sample/EVIDENCE_INDEX.md`, and `reports/public-sample/evidence-index.json`.
- [x] 3.2 Archive the OpenSpec change, sync the long-lived `hybrid-slot-representation-v1` spec, and generate a concise Chinese Human Brief.

## 4. Verification

- [x] 4.1 Run focused tests and full validation: `PYTHONPATH=src pytest -q`, `PYTHONPATH=src ruff check src tests`, `OPENSPEC_TELEMETRY=0 openspec validate --all --strict`, `python scripts/check_current_truth_surface.py`, `git diff --check`, and public leak scan.
- [x] 4.2 Review the final diff for scope boundaries and stop without implementing the recommended vertical slice.
