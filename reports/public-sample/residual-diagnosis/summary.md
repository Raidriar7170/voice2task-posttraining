# Residual Diagnosis Summary

- Manifest: `public-sample-20260617T152259Z`
- Scope: existing dev/test predictions only; recommendations are diagnostic and do not claim model improvement.

| split | total | strict pass | strict fail | top field |
| --- | ---: | ---: | ---: | --- |
| dev | 207 | 51 | 156 | `normalized_command` |
| test | 207 | 42 | 165 | `normalized_command` |

## Recommendations

- Keep safety and confirmation residuals in a dedicated fail-closed review boundary.
- Prioritize slot-key/schema-family review before adding training runs.
- Review deterministic canonicalization candidates separately from strict evaluator metrics.
- Use these residual counts to choose a later bounded remediation phase; do not treat them as model improvement.
