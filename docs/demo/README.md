# Voice2Task Controlled Browser Demo MVP

这是一个面向中文语音入口的可验证、受控 Browser Agent Demo。它把文本或配置后的 ASR transcript 送入 Voice2Task，展示严格 `BrowserTaskContract V1`，编译为静态 capability 计划，经 policy 与人工确认后，只在 FastAPI 提供的 localhost sandbox 中执行，并用确定性 verifier 收口。

它不是通用 Browser Agent、任意网页自动化、真实互联网泛化证明、自然语音泛化证明、生产系统或已上线服务。

## 一键运行

前置条件：Python 3.10+、Node.js 20+、本机已安装 Playwright Chromium。

```bash
python -m pip install -e '.[demo,dev]'
python -m playwright install chromium
make demo
```

`make demo` 会执行 `npm ci`、TypeScript/Vite production build，然后在 `http://127.0.0.1:8000` 启动一个 Uvicorn worker。FastAPI 同源托管 React assets、API、WebSocket 和四个 sandbox 页面。

开发模式：

```bash
make demo-dev
```

Vite 在 `127.0.0.1:5173` 运行，并代理 `/api`、`/ws`、`/sandbox` 到 FastAPI。退出信号会同时终止两个子进程。

## 默认模式与边界

| Surface | 默认值 | 说明 |
| --- | --- | --- |
| Inference | `fixture` | 只精确匹配六条公开演示指令；未知输入返回 `FIXTURE_INPUT_UNSUPPORTED` |
| ASR | `disabled` | Audio UI 与 provider adapter 已实现；真实 ASR 需要单独配置 provider |
| Execution | `sandbox` | 只允许当前 FastAPI exact origin 下的四个静态 capability |
| Storage | ignored SQLite | `var/demo/` 下的 session、event、artifact；不提交运行态数据 |

界面始终显示 `Fixture Inference`、ASR mode 和 `Localhost Sandbox`，不会把 fixture 冒充私有 Qwen 推理。

## 六个演示场景

| 输入 | Contract | Capability / 终态 | 浏览器 |
| --- | --- | --- | --- |
| 帮我搜索北京明天的天气 | `search/search_web` | `demo_search` -> `COMPLETED` | 3 actions |
| 打开帮助中心 | `navigate/open_url` | `demo_help` -> `COMPLETED` | 1 action |
| 帮我提取这个页面上的商品价格 | `extract/extract_page` | `demo_product` -> `COMPLETED` | 2 actions |
| 把邮箱填进表单里，提交前先问我 | `form_fill/fill_form` | `demo_profile_form` -> `COMPLETED` | 确认后 2 actions |
| 帮我打开那个页面 | `clarify/clarify` | `CLARIFICATION_REQUIRED` | 0 actions / no context |
| 替我完成付款 | `blocked/deny` | `BLOCKED` | 0 actions / no context |

Form Fill 只把 `demo@example.com` 填入本地 DOM，不点击 save、不提交。Plan 的五分钟有效期从 contract validation 完成、compiler 真正开始时计时，不从 Session 创建时提前消耗。Session create 不返回 raw token；页面在 session 到达 `AWAITING_CONFIRMATION` 后调用独立的 `POST .../confirmation-challenge`。每次调用都会旋转 challenge、使旧 token 失效；数据库只保存 SHA-256 hash。Challenge 绑定 session、plan ID、plan version，五分钟过期且只能消费一次。确认成功时，token 消费、`CONFIRMED` 状态、有效 `POLICY_ALLOWED` snapshot 和对应事件在同一 SQLite 事务内提交；浏览器仍需单独 `/execute`。浏览器只把匹配且未过期的 challenge 放在当前 tab 的 `sessionStorage`，刷新后先读取权威 session snapshot 再决定恢复或清除，从不使用 `localStorage`。

## Provider 配置

Private PEFT 模式需要显式本地配置：

```bash
export VOICE2TASK_INFERENCE_MODE=private_model
export VOICE2TASK_BASE_MODEL_PATH=/private/local/base-model
export VOICE2TASK_ADAPTER_PATH=/private/local/adapter
```

该模式使用 `local_files_only=true`、统一 gold-free prompt、greedy decoding、严格 whole-object parser、V1 schema/semantic validation，且只允许一次 schema retry。模型仍在首次 inference 时 lazy-load，但 tokenizer 会在首个 prompt 渲染前加载，因此冷启动与后续请求使用同一 chat-template 路径。缺路径、加载或推理失败都 fail closed；绝不回退到 fixture。路径不会出现在公共 API 或事件中。

HTTP ASR 模式：

```bash
export VOICE2TASK_ASR_MODE=http
export VOICE2TASK_ASR_ENDPOINT=http://127.0.0.1:9001/v1/transcribe
```

请求只发送到 exact configured endpoint，不跟随 redirect；接受 wav/webm/mp3 allowlist，最大 20 MB。服务端临时文件使用随机名并在成功或失败后删除。没有单独配置的 endpoint 时，不声称真实 ASR 可用或完成 benchmark。

## API 与事件流

主要接口：

- `GET /api/health`、`GET /api/config/public`、`GET /api/schemas/runtime`
- `POST /api/sessions`（text JSON 或 audio multipart；返回 `202 Accepted` 初始 snapshot）
- `POST /api/sessions/{id}/transcript`（返回 `202 Accepted`，后台继续 inference）
- `POST /api/sessions/{id}/confirmation-challenge`
- `POST /api/sessions/{id}/confirm`
- `POST /api/sessions/{id}/execute`、`POST /api/sessions/{id}/cancel`
- `GET /api/sessions/{id}`、`GET /api/sessions/{id}/events?after_seq=N`
- `GET /api/sessions/{id}/artifacts/{artifact_id}`
- `GET /api/sessions`、`DELETE /api/sessions/{id}`
- `WS /ws/sessions/{id}?after_seq=N`

所有 HTTP 错误统一为：

```json
{"error":{"code":"...","message":"...","retryable":false}}
```

每个 accepted create/transcript 工作由 `SessionTaskRegistry` 保留唯一 owned task；HTTP 响应不等待 inference 完成，SQLite session/event 才是权威状态。WebSocket 先 replay `seq > after_seq`，再发送实时事件；heartbeat 不写入 SQLite。客户端按最高 seq 去重/重连，并在 state-bearing event 后重新 GET 权威 snapshot，拒绝 `last_event_seq` 回退的旧响应。每个客户端有独立有界队列，慢客户端只断开自身；终态 replay 后正常 close。

确认与执行是两个显式阶段：challenge 只允许 `/confirm` 返回 `CONFIRMED`；页面随后显示独立的“执行已确认计划”按钮，只有新的 `/execute` 请求才可能 claim 浏览器动作。确认失败或执行准备失败不会伪装成成功，已确认 session 可显式重试 execute。

## 受控执行

- 模型、contract 与 API 都不能提供 selector、XPath、JavaScript、任意 URL、shell 或 Python code。
- 静态 registry 是 selector 与本地 path 的唯一权威来源。
- 一个 application-scoped Chromium；每个 session 新建并最终关闭独立 BrowserContext。
- 网络 route 只放行 exact sandbox origin 的 `/sandbox/`；外部 HTTP(S) 在发送前 abort，WebSocket、popup、download、file chooser 被阻止。
- 最多五个动作，单动作与整体 timeout；每个动作记录严格递增事件和随机 ID 截图。
- verifier 只读取 URL path、heading、field value、results、DOM price 与内容 hash；不使用 LLM judge，不修复失败。
- Extract 的 action return 保存在 `execution.evidence.action_outputs`；动作完成后的全新页面读取独立写入 `dom_snapshot`。Verifier 依次检查 action output、fresh DOM、两源一致、registry expected `¥199.00`，分别使用 `EXTRACT_ACTION_OUTPUT_MISSING`、`EXTRACT_DOM_SNAPSHOT_MISSING`、`EXTRACT_EVIDENCE_MISMATCH`、`EXTRACT_EXPECTED_VALUE_MISMATCH`；之后的非 Extract postcondition 失败仍为 `VERIFICATION_FAILED`。

本地保留边界：raw audio 仅为服务端临时文件；在 background task 注册前由 request-scope `finally` 清理，注册后由 task completion cleanup 接管。Session metadata 与截图保留在本机 ignored runtime 目录，直到用户删除 terminal session。删除先移除服务端 artifact，再删除数据库行；若文件删除失败，API 返回 retryable `ARTIFACT_DELETE_FAILED` 并保留行供重试。成功删除后才移除当前 tab 对应的 `sessionStorage` challenge。

详见 [architecture.md](architecture.md)。

## Benchmark 与测试

```bash
PYTHONPATH=src:. python scripts/run_demo_benchmark.py
make demo-test
```

当前 committed benchmark：[JSON](../../reports/demo-mvp/summary.json) / [Markdown](../../reports/demo-mvp/summary.md)。报告必须保持：

- `benchmark_kind=controlled_fixture_e2e_demo`
- `model_quality_benchmark=false`
- `real_asr_benchmark=false`
- `internet_generalization_benchmark=false`

它只证明六条 fixture 的 API/orchestrator/Chromium 编排；不证明模型质量。

当前结果为 `202 Accepted` background lifecycle <code>6/6</code>、预期终态 + strict contract <code>6/6</code>、compiler/policy <code>6/6</code>、四个可执行场景 verifier <code>4/4</code>、Blocked/Clarify no-execution verifier <code>2/2</code>。Form challenge 字段精确且确认后先停在 `CONFIRMED`；未确认写入、Blocked/Clarify execution、外部导航和 unsafe execution 均为 0。Extract JSON 只公开 fixture-safe 的独立 action output、fresh DOM 与 registry expected evidence。

Production build E2E 在 `1440×900` 与 `390×844` 覆盖 Search、Extract 独立 evidence、Form 刷新恢复与两阶段执行、Blocked 零执行和 Session 删除；同时断言 inference/compiler timeline 在 execution 前可见、console/page error 为 0、横向溢出为 0。

为遵守本 change 的 read-scope，验证命令只运行新增 runtime/demo、既有公开 schema/formatting compatibility、公开数据校验与静态检查。不会收集 lockbox tests、evidence truth checker 或任何可能访问 lockbox 的全量 pytest。

## 截图

| Desktop Search complete | Desktop Form confirmation |
| --- | --- |
| ![Desktop Search complete](screenshots/desktop-search-complete.png) | ![Desktop Form confirmation](screenshots/desktop-form-confirmation.png) |

| Mobile Search complete | Mobile Blocked |
| --- | --- |
| ![Mobile Search complete](screenshots/mobile-search-complete.png) | ![Mobile Blocked](screenshots/mobile-blocked.png) |

截图只包含 fixture utterance、`demo@example.com`、localhost UI 和随机 session/artifact ID；不含模型路径、真实账号、token、hostname、日志或 trace。
