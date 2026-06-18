# Canonical Slot Boundary Candidate Materialization

## Conclusion

This phase materialized public-safe canonical slot-boundary examples as
standalone report-local candidates only. They are review inputs, not formal
public sample rows, SFT rows, DPO pairs, predictions, model outputs, evaluator
changes, or training evidence.

## Source Policy

- Source policy directory:
  `reports/public-sample/slot-canonicalization-policy/`
- Source manifest id: `public-sample-20260617T152259Z`
- Source policy files:
  - `slot-key-policy.md`
  - `slot-value-policy.md`
  - `normalized-command-policy.md`
  - `model-target-boundary.md`
  - `summary.json`

## Accepted Candidate Groups

| group | examples | boundary |
| --- | ---: | --- |
| `slot_key_aliases` | 3 | alias-only slot-key review candidates |
| `slot_value_boundaries` | 4 | conservative value formatting candidates |
| `normalized_command_display_diagnostic` | 2 | display/diagnostic candidates only |

Representative examples:

- `search_text -> query` for the same public search intent.
- `site -> url` for the same public URL.
- `field/value -> field_name/field_value` for the same form-fill sketch.
- Leading/trailing whitespace trim for the same public query.
- Full-width punctuation review when named public fields stay unchanged.
- Request filler removal only when the concrete public entity is unchanged.
- Protocol/host URL casing review without path rewriting.
- `normalized_command` display examples that do not declare equivalence,
  repair predictions, or re-score prior residuals.

## Excluded Non-Equivalence Examples

The report records these explicit exclusions so later phases cannot silently
normalize them:

- `date_today_vs_tomorrow`
- `city_origin_vs_destination`
- `product_name_change`
- `url_host_change`
- `price_amount_change`
- `product_name_vs_query`
- `location_vs_destination`
- `action_vs_reason`

All excluded examples have `merge_allowed=false` and
`formal_public_sample_status=not_added`.

## Standalone Boundary

The machine-readable report records:

- no formal public sample data mutation;
- no SFT or DPO row generation;
- no manifest rebuild or split change;
- no evaluator definition or metric change;
- no prediction run, training run, or A100 job;
- no deterministic postprocessor implementation;
- no strict-exact relaxation, LLM judge, semantic-equivalence scoring,
  prediction repair, checkpoint release, or adapter release.

## Claims Not Made

This phase does not claim model improvement, held-out recovery, production
readiness, safety readiness, or live-browser benchmark improvement.

## Files

- `reports/public-sample/canonical-slot-boundary-candidates/summary.json`
- `reports/public-sample/canonical-slot-boundary-candidates/summary.md`
- `reports/public-sample/canonical-slot-boundary-candidates/leak_scan_result.json`
- `docs/human-briefs/2026-06-18-materialize-canonical-slot-boundary-candidates.html`

