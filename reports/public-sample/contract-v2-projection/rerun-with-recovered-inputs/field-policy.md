# Contract V2 Projection Field Policy

- Core fields are copied from valid parsed V1 contracts without repair.
- `normalized_command`, `language`, and `contract_version` are derived envelope fields.
- The renderer reads only V2 Core fields and bounded templates.
- Slot keys and values are not merged, substituted, or semantically rescored.
- Unsupported renderer shapes fail closed.
