# Slot Key Policy

This file defines deterministic slot-key writing guidance. It is schema policy, not semantic guessing, and it does not change strict evaluator behavior.

## Canonical Keys

- `query`: search intent text.
- `url`: target URL or public example URL.
- `field_name`: form or extracted field name.
- `field_value`: value to enter into a form field.
- `target`: extraction target such as `商品价格`.
- `ambiguity`: missing information that requires clarification.
- `reason`: blocked or refusal reason.
- `amount`, `date`, `city`, `destination`, `product_name`, `action`: task-scoped slots only.

## Alias To Canonical

| alias | canonical |
| --- | --- |
| `keyword`, `keywords`, `search_text`, `search_term`, `q` | `query` |
| `webpage`, `page`, `site`, `website` | `url` |
| `field`, `form_field`, `input_field` | `field_name` |
| `value`, `input_value` | `field_value` |

Alias mapping is deterministic. A later implementation may apply it to diagnostics or data materialization, but this phase only documents the policy.

## Task-Type Boundaries

| task type | required slots | optional slots |
| --- | --- | --- |
| `search` | `query` | `date`, `city` |
| `navigate` | `url` | none |
| `form_fill` | `field_name`, `field_value` | `url` |
| `extract` | `target` | `url`, `query`, `field_name` |
| `clarify` | `ambiguity` | none |
| `blocked` | `reason` | `action` |

## Disallowed Keys

Do not emit `raw_transcript`, `asr_text`, `debug`, `notes`, `private_path`, `runtime_hint`, `allowed_actions`, or `success_criteria` as model-predicted slots.

## Missing And Extra Slot Guidance

- Missing required task-scoped slots remain strict failures.
- Extra slots are not silently dropped in strict exact.
- Alias-only key differences may be reviewed in a later deterministic diagnostic or data materialization phase.
- Non-equivalent fields must not be merged.

## Non-Equivalence Cases

- `product_name` vs `query`: Do not merge. A product identifier is not always the same as a search intent.
- `location` vs `destination`: Do not merge. Origin, current location, filter city, and destination can carry different semantics.
- `action` vs `reason`: Do not merge. A blocked action and a refusal reason support different review surfaces.

## Public-Safe Examples

- `{"search_text": "厦门轮渡时刻表"}` may canonicalize to `{"query": "厦门轮渡时刻表"}` in a later bounded phase.
- `{"site": "https://example.com"}` may canonicalize to `{"url": "https://example.com"}` in a later bounded phase.
- `{"field": "备注", "value": "请尽快处理"}` may canonicalize to `{"field_name": "备注", "field_value": "请尽快处理"}`.
