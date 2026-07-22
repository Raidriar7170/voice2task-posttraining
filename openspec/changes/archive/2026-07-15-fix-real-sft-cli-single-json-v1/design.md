## Context

The CLI currently dispatches directly to training functions and prints the returned public result afterward. During the first authorized real one-step SFT process, the Transformers/TRL `PrinterCallback` wrote two Python mapping representations to stdout before the final result JSON. The process exited zero and the returned adapter metadata contained real update evidence, but the complete stdout was not one JSON document, so the runtime postcondition failed.

The contract belongs at the CLI process boundary: output can be emitted while loading dependencies, constructing trainers, invoking callbacks, or training. Isolating only `trainer.train()` would leave other downstream sources able to contaminate stdout. The CLI runs one synchronous command per process, and long-running output must stream instead of accumulating in memory.

## Goals / Non-Goals

**Goals:**

- Reserve CLI stdout for exactly one final sanitized result JSON on both success and failure.
- Preserve downstream Python stdout as diagnostic stderr with a non-JSON line prefix.
- Keep the existing public result allowlist and typed exit-code mapping unchanged.
- Cover noisy SFT success, noisy runtime failure, and the shared DPO dispatch boundary without executing training.

**Non-Goals:**

- No second real smoke, model loading, GPU work, full SFT, DPO, GRPO, prediction, evaluation, or lockbox access.
- No change to training budgets, model/data selection, clean-evaluation truth, adapter evidence, or output-directory policy.
- No interception of native code or subprocesses that bypass Python `sys.stdout` and write directly to file descriptor 1.

## Decisions

### Isolate at the unified CLI dispatch boundary

All backend command dispatch will run inside `contextlib.redirect_stdout(...)`; final success and sanitized exception JSON printing will remain outside that context. This covers SFT, DPO, preflight, and other CLI backends consistently, and guarantees stdout restoration before the exception handler writes the only failure result.

Alternative considered: redirect only around SFT `trainer.train()`. Rejected because model/tokenizer loading, trainer construction, callbacks, and DPO can also print before or outside that call.

### Stream diagnostics to a prefixed stderr adapter

The redirect target will forward data to the current stderr stream and add a stable non-JSON prefix at each logical line start. This preserves progress without retaining potentially long training logs and prevents a backend-emitted JSON line from being mistaken for the CLI result document.

Alternative considered: redirect directly to stderr. Rejected because a downstream valid JSON object could then be misread as a second result. Alternative considered: capture in `StringIO`. Rejected because training logs are unbounded relative to this smoke contract.

### Test the observed failure shape without loading models

Regression tests will monkeypatch backend functions to print the two observed Python mapping forms before returning or raising. They will parse the complete stdout with `json.loads`, verify exit status/result status, and verify stderr diagnostics are prefixed and contain no independently parseable training-result document. DPO coverage uses the same mock-only dispatch test and does not authorize DPO execution.

## Risks / Trade-offs

- [Risk] `redirect_stdout` changes process-global `sys.stdout` and is not thread-local. → The CLI is a synchronous one-command process; document and test this boundary without exposing it as a concurrent library API.
- [Risk] A custom stream adapter may receive partial writes. → Track line-start state across writes and test multiple lines plus a final line without a newline.
- [Risk] Native code can write directly to file descriptor 1. → This bounded fix addresses the observed Python callback path; no claim is made about OS-level descriptor capture.
- [Risk] Prefixing changes diagnostic formatting. → Use one stable public-safe prefix and keep all result semantics exclusively on stdout.
