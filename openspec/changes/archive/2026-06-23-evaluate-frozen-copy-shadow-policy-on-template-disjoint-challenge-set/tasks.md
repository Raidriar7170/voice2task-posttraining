## 1. Hook Hardening

- [x] 1.1 Add tests for rejecting non-default `retain_input_text`, `retain_raw_model_output`, and `fail_isolated=false` without mutating primary prediction output.
- [x] 1.2 Add tests for run-level policy load-once behavior, policy hash/version propagation, and policy drift detection.
- [x] 1.3 Add tests for sidecar path conflicts with prediction output, prediction metadata, prompt snapshot, raw decoded summary, and generation trace artifacts.
- [x] 1.4 Implement reserved config rejection, immutable run-level policy snapshot reuse, post-run policy drift audit, and conflict-isolated sidecar sink behavior.

## 2. Challenge Set Materialization

- [x] 2.1 Add deterministic challenge row generation for `copy-shadow-template-disjoint-challenge-v1` with enabled-scope balance, negative controls, condition tags, synthetic PII labels, template signatures, input hashes, and gold hashes.
- [x] 2.2 Add public-safety, template-disjoint, near-duplicate, and current train/dev/test overlap audits with thresholded row rejection.
- [x] 2.3 Add gold contract validation and gold verifier feasibility checks for exact unique, duplicate exact, source absent, normalization candidate/collision, partial span, and out-of-scope action conditions.
- [x] 2.4 Write frozen challenge rows to `data/public-samples/copy-shadow-template-disjoint-challenge-v1.jsonl` and manifest/audit artifacts under `reports/public-sample/copy-shadow-template-disjoint-challenge-v1/`.

## 3. Challenge Prediction and Evaluation

- [x] 3.1 Discover and verify frozen adapter identity/config metadata; if unavailable, write `blocked.json` with `CHALLENGE_EVALUATION_BLOCKED` and stop without fabricating predictions.
- [x] 3.2 Record canonical prediction as blocked by 3.1 before inference because no identity-verifiable loadable frozen adapter is available; no shadow-disabled/NullSink/JsonlSink challenge predictions were fabricated.
- [x] 3.3 Record gold-free online sidecar and offline EvaluationAudit generation as blocked by 3.1; no sidecars or correctness joins were fabricated after the adapter gate failed closed.
- [x] 3.4 Record prediction output invariance, parsed contract invariance, evaluator input invariance, runtime decision invariance, deterministic hook behavior, and V1 metric zero-delta as unproven/blocked for challenge inference.

Blocked note: 3.2-3.4 were not run because 3.1 found no local identity-verifiable loadable frozen adapter. The report writes `CHALLENGE_EVALUATION_BLOCKED` and does not fabricate predictions.

## 4. Metrics and Reports

- [x] 4.1 Generate pipeline integrity, scope coverage, correctness audit, adversarial condition, Wilson interval, latency, policy-freeze, privacy, and recommended-next-change reports.
- [x] 4.2 Select exactly one bounded decision label from the spec and include scope retain/narrow/disable recommendations without modifying the frozen policy.
- [x] 4.3 Add `docs/copy-shadow-template-disjoint-challenge.md`, README/README_en/CONTEXT/evidence-index updates, and a concise Chinese Human Brief.

## 5. Verification, Review, and Archive

- [x] 5.1 Run focused tests, functional full pytest excluding the active-change truth-surface gate, `ruff check .`, `OPENSPEC_TELEMETRY=0 openspec validate --all --strict`, pre-archive `python scripts/check_current_truth_surface.py`, `git diff --check`, public leak scan, template-disjoint audit, challenge freeze check, and policy drift check; challenge prediction invariance remains explicitly blocked by 3.1.
- [x] 5.2 Run a read-only Reviewer subagent over the final diff, fix Must Fix findings only, and rerun relevant verification.
- [x] 5.3 Archive the OpenSpec change after the blocked terminal path is documented and stop without creating policy-v2, challenge-v2, runtime enforcement, training, action enablement, or normalized trusted provenance.
