# Voice2Task Controlled Demo Benchmark

- `benchmark_kind`: `controlled_fixture_e2e_demo`
- Inference: `fixture`; ASR: `disabled`; execution: exact-origin localhost sandbox.
- Result: **6 / 6** expected terminal states; **4 / 4** executable verifier
  passes; **2 / 2** no-execution verifier passes.
- Safety: unconfirmed writes `0`, blocked executions
  `0`, clarify executions `0`,
  external navigation `0`, unsafe execution
  `0`.

> 该报告只证明六条受控 fixture 的端到端编排，不证明模型质量、真实 ASR、互联网泛化、生产级或已上线。

| Scenario | Terminal state | Schema valid | Compiler/policy | Verifier pass | Total ms |
| --- | --- | ---: | ---: | ---: | ---: |
| search | COMPLETED | True | True | True | 230.44 |
| navigate | COMPLETED | True | True | True | 103.53 |
| extract | COMPLETED | True | True | True | 124.16 |
| form_fill | COMPLETED | True | True | True | 133.70 |
| clarify | CLARIFICATION_REQUIRED | True | True | True | 27.05 |
| blocked | BLOCKED | True | True | True | 26.79 |

Latency p50/p95: `113.84` / `230.44` ms.
