# Copy-shadow scope policy v2 design

Decision: `POLICY_V2_SCOPE_REDUCTION_READY_FOR_REVIEW`.

Policy V2 is proposal-only. It is inactive, not runtime loaded, not enforcement, not action eligibility, not normalized trust, not training, not model improvement, and not a production or safety readiness claim.

## Scope decisions

- `extract:extract_page:target`: original `INSUFFICIENT_EVIDENCE`, final `INSUFFICIENT_EVIDENCE`
- `form_fill:fill_form:field`: original `PROPOSE_DISABLE`, final `PROPOSE_DISABLE`
- `search:search_web:query`: original `INSUFFICIENT_EVIDENCE`, final `INSUFFICIENT_EVIDENCE`

## Evidence

- Challenge hash: `12eccdd54b2c89f1127ec23f18d7179e1ebaacb1a644ae5ca1a14b3309f11324`
- Policy V1 hash: `5dc14efb8ded13dc048ddb067c7c63a1a62b6c03896950e861303973d505cbc7`
- Technical false accepts: `0`
- Execution eligible count: `0`

Recommended next change: `review-and-freeze-copy-shadow-policy-v2-before-naturalistic-challenge`.
