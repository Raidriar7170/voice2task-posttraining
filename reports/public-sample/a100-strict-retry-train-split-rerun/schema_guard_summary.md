# Strict-Retry Schema Guard Summary

This report preserves observed raw and retry attempt evidence. Strict retry requires the full retry output to be a JSON object; JSON fragments wrapped in Markdown or prose remain invalid.

## Counts

- Predictions: `3`
- Raw attempt schema-valid: `0`
- Retry attempted: `3`
- Retry attempt schema-valid: `0`
- Strict retry rejected fragment count: `3`
- Validated output schema-valid: `0`
- Validated output source counts: `{'none': 3}`

## Rows

- `seed-search-weather`: raw=`False` (non_json), retry=`False` (json_fragment_object), validated=`False` via `none`
- `seed-search-weather-aug-1`: raw=`False` (json_object), retry=`False` (json_fragment_object), validated=`False` via `none`
- `seed-search-weather-aug-2`: raw=`False` (json_object), retry=`False` (json_fragment_object), validated=`False` via `none`
