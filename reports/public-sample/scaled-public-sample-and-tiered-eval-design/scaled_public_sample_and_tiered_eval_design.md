# Voice2Task scaled public sample and tiered evaluation design

This is a design-only public evidence report. It does not materialize seeds, rebuild SFT/DPO, train, predict, repair predictions, change prompts, or relax evaluator metrics.

## Boundary

- Formal public sample modified: `False`.
- Seed/SFT/DPO/manifest files rebuilt: `False`.
- Training or prediction run: `False`.
- Evaluator metric change or relaxation: `False`.
- strict `contract_exact_match` and strict `slot_f1` remain public headline metrics.
- `slot_f1_soft` and partial tier matches remain diagnostic-only.

## Current Evidence

- Dataset manifest: `public-sample-20260617T045941Z`
- Current seed rows: `102`
- Current SFT rows: `261`
- Current DPO pairs: `881`
- Current SFT split counts: `{'dev': 69, 'test': 69, 'train': 123}`
- Current seed split counts: `{'train': 56, 'dev': 23, 'test': 23}`
- Task-type coverage: `{'search': 10, 'navigate': 13, 'form_fill': 42, 'blocked': 15, 'extract': 10, 'clarify': 12}`
- Safety reason coverage: `{'public_readonly': 33, 'requires_confirmation': 42, 'unsafe_payment': 15, 'ambiguous_request': 12}`
- Confirmation coverage: `{'False': 35, 'True': 67}`
- Average variants per seed: `2.559`

## Latest Model Evidence

### `dev`

- strict contract exact: `0.43478260869565216`
- strict slot F1: `0.5579710144927537`
- diagnostic soft slot F1: `0.8332347431726314`
- task/route accuracy: `0.8840579710144928` / `0.8840579710144928`
- safety recall: `1.0`
- confirmation accuracy: `0.927536231884058`
- failure counts: slot `31`, route `8`, confirmation `5`, safety `0`

### `test`

- strict contract exact: `0.37681159420289856`
- strict slot F1: `0.5458937198067634`
- diagnostic soft slot F1: `0.7949706841735827`
- task/route accuracy: `0.927536231884058` / `0.927536231884058`
- safety recall: `1.0`
- confirmation accuracy: `0.9855072463768116`
- failure counts: slot `34`, route `5`, confirmation `1`, safety `1`

## Scaled Public-Sample Target

- Target seed milestone: `240`
- Target core bucket total: `220`
- Target overlay bucket total: `20`
- Recommended next step: `materialize_scaled_public_sample_candidates_after_review`

### `search`

- Current seed rows: `10`
- Target seed rows: `30`
- Counts toward target seed milestone: `True`
- Augmentation guidance: `4-6 variants per seed; keep compact query slots stable.`
- Accepted contract sketch: `{'task_type': 'search', 'route': 'search_web', 'slots': ['query']}`
- Rejected drift sketches: `['query paraphrase changes slot value', 'search intent routed to navigate']`

### `navigation`

- Current seed rows: `13`
- Target seed rows: `30`
- Counts toward target seed milestone: `True`
- Augmentation guidance: `4-6 variants per seed; keep canonical URL exact.`
- Accepted contract sketch: `{'task_type': 'navigate', 'route': 'open_url', 'slots': ['url']}`
- Rejected drift sketches: `['URL loses scheme', 'public navigation incorrectly requires confirmation']`

### `form_fill`

- Current seed rows: `42`
- Target seed rows: `45`
- Counts toward target seed milestone: `True`
- Augmentation guidance: `5-8 variants per seed; separate field specificity and confirmation markers.`
- Accepted contract sketch: `{'task_type': 'form_fill', 'route': 'fill_form', 'slots': ['field', 'value']}`
- Rejected drift sketches: `['field becomes generic', 'submit/payment intent loses confirmation']`

### `extract`

- Current seed rows: `10`
- Target seed rows: `35`
- Counts toward target seed milestone: `True`
- Augmentation guidance: `5-7 variants per seed; preserve target wording and avoid search fallback.`
- Accepted contract sketch: `{'task_type': 'extract', 'route': 'extract_page', 'slots': ['target']}`
- Rejected drift sketches: `['extract routed to search_web', 'target slot adds generic price wording']`

### `clarify`

- Current seed rows: `12`
- Target seed rows: `45`
- Counts toward target seed milestone: `True`
- Augmentation guidance: `6-8 variants per seed; emphasize underspecified-but-action-shaped requests.`
- Accepted contract sketch: `{'task_type': 'clarify', 'route': 'clarify', 'slots': ['ambiguity']}`
- Rejected drift sketches: `['ambiguous request guessed as form_fill', 'missing target guessed as extract']`

### `blocked_payment`

- Current seed rows: `15`
- Target seed rows: `35`
- Counts toward target seed milestone: `True`
- Augmentation guidance: `5-8 variants per seed; cover payment, purchase, refund, subscription actions.`
- Accepted contract sketch: `{'task_type': 'blocked', 'route': 'deny', 'safety': {'allow': False, 'reason': 'unsafe_payment'}}`
- Rejected drift sketches: `['unsafe payment allowed', 'blocked payment downgraded to form_fill']`

### `confirmation_boundary`

- Current seed rows: `67`
- Target seed rows: `20`
- Counts toward target seed milestone: `False`
- Augmentation guidance: `Overlay bucket; pair similar requests that differ only by confirmation marker.`
- Accepted contract sketch: `{'confirmation_required': [True, False]}`
- Rejected drift sketches: `['confirmation marker ignored', 'confirmation inferred where absent']`

## Tiered Evaluation Design

### `T0_schema_structure`

- Existing metrics: `['json_valid_rate', 'failure_slices.schema']`
- Diagnostic question: `Can the model emit schema-valid BrowserTaskContract JSON?`
- Data decision: `If this fails, fix rendering/objective before adding more semantic cases.`
- Public claim role: `gating`

### `T1_task_route`

- Existing metrics: `['task_type_accuracy', 'route_accuracy', 'failure_slices.task_type', 'failure_slices.route']`
- Diagnostic question: `Does the model choose the correct contract family and route?`
- Data decision: `Add contrastive boundary seeds for clarify/extract/form_fill/navigate if this tier fails.`
- Public claim role: `diagnostic`

### `T2_safety_confirmation`

- Existing metrics: `['safety_precision', 'safety_recall', 'confirmation_accuracy']`
- Diagnostic question: `Are stop decisions and confirmation markers preserved?`
- Data decision: `Add paired safety and confirmation boundary seeds before retraining.`
- Public claim role: `diagnostic`

### `T3_slot_exactness`

- Existing metrics: `['slot_f1', 'failure_slices.slot', 'slot_f1_soft']`
- Diagnostic question: `Are strict slot keys and values exact, and where are near misses concentrated?`
- Data decision: `Use strict slot failures for data design; keep soft slot F1 diagnostic-only.`
- Public claim role: `headline_for_strict_slot_f1_only`

### `T4_full_contract_exact`

- Existing metrics: `['contract_exact_match']`
- Diagnostic question: `Does the complete contract match exactly?`
- Data decision: `Use as final public held-out success metric after lower tiers are stable.`
- Public claim role: `headline`

## Recommended Next Step

Review this design, then open a later bounded materialization phase for scaled public-sample candidates. Do not treat this report as data generation, model recovery, production readiness, or a reason to replace strict headline metrics.
