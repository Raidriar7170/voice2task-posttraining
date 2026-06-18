# Slot Value Policy

This policy is conservative design guidance only. It does not affect strict exact-match scoring, does not repair predictions, and does not re-score prior evidence.

## Safe Canonicalization Types

- Trim leading and trailing whitespace.
- Normalize full-width and half-width punctuation where the value itself is unchanged.
- Remove purely filler request words only when the entity, date, amount, URL, field, and user intent remain unchanged.
- Normalize ASCII casing for URLs and emails only where protocol/domain semantics allow it.
- Normalize punctuation and spacing inside phone-like or code-like values only when the canonical representation is specified by a later data policy.

## Chinese Filler And Request Words

Filler such as `帮我`, `麻烦`, `请`, or duplicated request verbs may be removed only if the slot value still names the same concrete entity or intent. Common verb/request-word handling must not erase the difference between searching, opening, filling, extracting, clarifying, and refusing.

## Numeric, Date, Price, City, Product, URL, Email, Phone

- Numbers and amounts: Do not merge changed quantities, units, or price bounds.
- Dates: Do not merge `今天`, `明天`, `周五`, or absolute dates unless a later policy defines the exact date reference and comparison boundary.
- Prices: Do not merge `门票`, `门票价格`, and `最低价` by default.
- Cities and places: Do not merge origin, destination, current location, or filter city outside task-specific context.
- Product names: Do not merge distinct product names or product/category substitutions.
- URLs: Do not merge host, path, or protocol changes.
- Emails and phones: Do not merge character, digit, domain, or country-code changes.

## Do Not Merge

- `今天` vs `明天`
- `厦门轮渡时刻表` vs `厦门轮渡时间`
- `武汉明天温度` vs `武汉明天天气`
- `https://map.example.com` vs `https://maps.example.com`
- `payment_requires_user_control` vs `purchase_control`

## Metric Boundary

Slot-value normalization in this document is design and diagnostic guidance only. It does not affect strict exact-match scoring, strict slot F1, prior layered metrics, or residual diagnosis counts.

