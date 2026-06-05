# A100 normalized-command policy schema guard summary

Status: schema-guard and retry evidence from one private-adapter A100 train-split rerun.

- Raw-attempt schema-valid: `1/3`
- Retry attempted: `2/3`
- Retry-attempt schema-valid: `0/3`
- Final validated schema-valid: `1/3`
- Normalized-command exact-string matches: `2/3`
- Schema repair applied: `False`
- Strict retry parser rejects Markdown/prose-wrapped fragments: `True`

The rerun reached the private A100 adapter path and included the normalized-command prompt policy. It still leaves two final rows schema-invalid, so this must not be described as full train-row recovery.
