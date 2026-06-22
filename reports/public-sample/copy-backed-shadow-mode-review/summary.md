# Copy-backed Shadow Interface Review

Decision: `SHADOW_INTERFACE_READY_FOR_PREDICTION_HOOK`.

This is a review-and-hardening phase before any prediction-pipeline shadow hook. It is not runtime wiring or enforcement.

## Core Counts

- Online sidecars: 828/828.
- Evaluation audit rows: 942.
- Total slot events: 942.
- Eligible slot events: 430.
- Trusted exact: 376 (0.874419 over eligible).
- Eligible verification failures: 54 (0.125581 over eligible).
- Out of scope: 512 (0.543524 over total).
- Trusted exact and gold-correct: 347 (0.922872 over trusted exact).
- Trusted exact but gold-mismatch: 29 (0.077128 over trusted exact).

## Gates

- Normalized trusted count: 0.
- Action trusted count: 0.
- Provenance false accepts: 0.
- Silent fallbacks: 0.
- Contract mutation count: 0.
- Runtime decision delta count: 0.
- V1 evaluator metric delta zero: True.
- Deterministic rerun rate: 1.000000.

## Per-scope Review

- Highest trusted exact rate: `extract:extract_page:target`.
- Highest not-found count: `form_fill:fill_form:field`.
- Highest gold-mismatch rate: `search:search_web:query`.
- Scope disable recommendations: [].

## Latency

- Policy lookup p95: 0.000083 ms.
- Exact unique lookup p95: 0.001750 ms.
- Full span validation p95: 0.000542 ms.
- Sidecar serialization p95: 0.006250 ms.

## Next

Next change: `integrate-copy-backed-verification-prediction-shadow-hook`. Attach the gold-free OnlineShadowSidecar to the prediction pipeline in shadow mode only, still with no runtime enforcement.
