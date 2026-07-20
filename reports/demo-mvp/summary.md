# Voice2Task Controlled Demo Benchmark

- `benchmark_kind`: `controlled_fixture_e2e_demo`
- Claim flags: `model_quality_benchmark=false`; `real_asr_benchmark=false`;
  `internet_generalization_benchmark=false`.
- Inference: `fixture`; ASR: `disabled`; execution: exact-origin localhost sandbox.
- Result: **6 / 6** expected terminal states; **4 / 4** executable verifier
  passes; **2 / 2** no-execution verifier passes.
- Contract/compiler: **6 / 6** terminal + strict contract;
  **6 / 6** compiler/policy. All six creates returned
  `202 Accepted` with the initial background-work snapshot.
- Confirmation: challenge fields were exact and the write plan stopped at `CONFIRMED` before a
  separate `/execute` request (`1 / 1`).
- Safety: unconfirmed writes `0`, blocked executions
  `0`, clarify executions `0`,
  external navigation `0`, unsafe execution
  `0`.

> 该报告只证明六条受控 fixture 的端到端编排，不证明模型质量、真实 ASR、互联网泛化、生产级或已上线。

| Scenario | Terminal state | Schema valid | Compiler/policy | Verifier pass | Total ms |
| --- | --- | ---: | ---: | ---: | ---: |
| search | COMPLETED | True | True | True | 246.69 |
| navigate | COMPLETED | True | True | True | 120.59 |
| extract | COMPLETED | True | True | True | 132.81 |
| form_fill | COMPLETED | True | True | True | 151.02 |
| clarify | CLARIFICATION_REQUIRED | True | True | True | 36.30 |
| blocked | BLOCKED | True | True | True | 37.57 |

Latency p50/p95: `126.7` / `246.69` ms.

Extract evidence is serialized only for the Extract scenario as independent
`action_outputs`, fresh `dom_snapshot`, and registry-owned expected values in the JSON report.
