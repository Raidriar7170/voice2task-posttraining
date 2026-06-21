# Contract V2 Projection Spec

Status: blocked before metric execution.

This phase would project V1 Browser Task Contract objects into an experimental
V2 Core containing only:

- `task_type`
- `route`
- `safety.allow`
- `safety.reason`
- `confirmation_required`
- `slots`

The V2 Core intentionally excludes:

- `normalized_command`
- `language`
- `contract_version`

`language` would be fixed by an envelope/postprocessor as `zh-CN`.
`contract_version` would be fixed by an envelope/postprocessor as `v2`.
`normalized_command` would be a display / diagnostic field rendered
deterministically when a bounded template supports the task and slot pattern.

This spec remains experimental. It does not modify `BrowserTaskContract` V1,
the strict evaluator, layered evaluator semantics, runtime consumers, training
targets, prompts, splits, predictions, or data artifacts.

Projection metrics were not computed because the latest committed step-matched
evidence root lacks raw Control/Treatment dev/test prediction contracts and
dev/test gold JSONL contracts.
