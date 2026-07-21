import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "../App";
import { challengeStorageKey } from "../lib/confirmationChallenge";
import type { ExecutionEvent, SessionRecord, SessionStatus } from "../types";

class ControlledWebSocket {
  static OPEN = 1;
  static instances: ControlledWebSocket[] = [];
  readonly url: string;
  readyState = 1;
  onopen: (() => void) | null = null;
  onmessage: ((event: MessageEvent<string>) => void) | null = null;
  onclose: ((event: CloseEvent) => void) | null = null;
  onerror: (() => void) | null = null;

  constructor(url: string) {
    this.url = url;
    ControlledWebSocket.instances.push(this);
    queueMicrotask(() => this.onopen?.());
  }

  emit(event: ExecutionEvent) {
    this.onmessage?.({ data: JSON.stringify(event) } as MessageEvent<string>);
  }

  close(code = 1000) {
    this.onclose?.({ code } as CloseEvent);
  }
}

const config = {
  inference_mode: "fixture",
  asr_mode: "disabled",
  execution_mode: "sandbox",
  benchmark_kind: "controlled_fixture_e2e_demo",
};

function makeSession(
  status: SessionStatus,
  {
    id = "session-one",
    seq = 2,
    confirmation = false,
  }: { id?: string; seq?: number; confirmation?: boolean } = {},
): SessionRecord {
  const terminal = ["COMPLETED", "BLOCKED", "CLARIFICATION_REQUIRED", "FAILED", "CANCELLED"].includes(status);
  return {
    id,
    created_at: "2026-07-20T00:00:00Z",
    updated_at: `2026-07-20T00:00:${String(seq).padStart(2, "0")}Z`,
    status,
    input_kind: "text",
    context: {
      session_id: id,
      profile: { email: "demo@example.com" },
      selected_capability: confirmation ? "demo_profile_form" : "demo_help",
      plan_version: 1,
      plan_issued_at: "2026-07-20T00:00:00Z",
    },
    transcript_original: confirmation ? "把邮箱填进表单里，提交前先问我" : "打开帮助中心",
    transcript: confirmation ? "把邮箱填进表单里，提交前先问我" : "打开帮助中心",
    transcript_edited: false,
    inference_mode: "fixture",
    asr_mode: "disabled",
    execution_mode: "sandbox",
    contract: status === "INPUT_RECEIVED" ? null : {
      task_type: confirmation ? "form_fill" : "navigate",
      route: confirmation ? "fill_form" : "open_url",
      safety: { allow: true, reason: confirmation ? "requires_confirmation" : "public_readonly" },
      confirmation_required: confirmation,
      slots: confirmation ? { field: "邮箱" } : { url: "https://help.example.com" },
      normalized_command: confirmation ? "填写邮箱并确认" : "打开帮助中心",
      language: "zh-CN",
      contract_version: "v1",
    },
    contract_validation: null,
    plan: status === "INPUT_RECEIVED" ? null : {
      plan_id: "plan-one",
      session_id: id,
      plan_version: 1,
      route: confirmation ? "fill_form" : "open_url",
      capability_id: confirmation ? "demo_profile_form" : "demo_help",
      requires_confirmation: confirmation,
      actions: [],
      postconditions: [],
      max_actions: 5,
      expires_at: "2099-07-20T00:05:00Z",
    },
    policy: status === "INPUT_RECEIVED" ? null : {
      allowed: !confirmation || status === "CONFIRMED",
      requires_confirmation: confirmation,
      reason_code: confirmation ? "CONFIRMATION_REQUIRED" : "POLICY_ALLOWED",
      message: confirmation ? "Explicit confirmation is required" : "Allowed",
    },
    execution: terminal && status === "COMPLETED" ? {
      browser_context_created: true,
      action_count: 1,
      final_url_path: "/sandbox/help",
      evidence: { action_outputs: {}, dom_snapshot: {} },
      screenshots: ["shot-one"],
      elapsed_ms: 1,
    } : null,
    verification: null,
    error_code: null,
    plan_version: 1,
    confirmation_status: confirmation ? "pending" : "not_required",
    confirmation_plan_id: confirmation ? "plan-one" : null,
    confirmation_expires_at: confirmation ? "2099-07-20T00:05:00Z" : null,
    confirmation_consumed_at: status === "CONFIRMED" ? "2026-07-20T00:01:00Z" : null,
    execution_claimed: status === "EXECUTING" || status === "VERIFYING" || status === "COMPLETED",
    cancel_requested: status === "CANCELLED",
    last_event_seq: seq,
  };
}

function event(eventType: string, seq: number, sessionId = "session-one"): ExecutionEvent {
  return {
    session_id: sessionId,
    seq,
    event_type: eventType,
    stage: "session",
    status: "ok",
    message: eventType,
    payload: {},
    created_at: "2026-07-20T00:00:00Z",
  };
}

function json(payload: unknown, status = 200): Response {
  return new Response(JSON.stringify(payload), { status });
}

beforeEach(() => {
  ControlledWebSocket.instances = [];
  sessionStorage.clear();
  localStorage.clear();
  vi.stubGlobal("WebSocket", ControlledWebSocket);
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe("async application lifecycle", () => {
  it("restores replay events before opening the recent session WebSocket", async () => {
    const recent = makeSession("PLAN_READY", { seq: 7 });
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const url = String(input);
      if (url.endsWith("/api/config/public")) return json(config);
      if (url.endsWith("/api/sessions")) return json({ sessions: [recent] });
      if (url.endsWith(`/api/sessions/${recent.id}`)) return json({ session: recent });
      if (url.includes("/events")) return json({ events: [event("PLAN_COMPILED", 7)] });
      throw new Error(`unexpected request ${url}`);
    });

    render(<App />);

    expect((await screen.findAllByText("PLAN_COMPILED"))[0]).toBeVisible();
    await waitFor(() => expect(ControlledWebSocket.instances).toHaveLength(1));
    expect(ControlledWebSocket.instances[0].url).toContain("after_seq=7");
  });

  it("refreshes a history snapshot when replay is already newer", async () => {
    const stale = makeSession("INPUT_RECEIVED", { seq: 2 });
    const planned = makeSession("PLAN_READY", { seq: 7 });
    let snapshotReads = 0;
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const url = String(input);
      if (url.endsWith("/api/config/public")) return json(config);
      if (url.endsWith("/api/sessions")) return json({ sessions: [planned] });
      if (url.endsWith(`/api/sessions/${planned.id}`)) {
        snapshotReads += 1;
        return json({ session: snapshotReads === 1 ? stale : planned });
      }
      if (url.includes("/events")) return json({ events: [event("PLAN_COMPILED", 7)] });
      throw new Error(`unexpected request ${url}`);
    });

    render(<App />);

    expect((await screen.findAllByText("计划待执行"))[0]).toBeVisible();
    expect(snapshotReads).toBe(2);
    await waitFor(() => expect(ControlledWebSocket.instances).toHaveLength(1));
    expect(ControlledWebSocket.instances[0].url).toContain("after_seq=7");
  });

  it("does not let a slower history selection overwrite the newer selection", async () => {
    const first = makeSession("PLAN_READY", { id: "session-first", seq: 7 });
    first.transcript = "first transcript";
    const second = makeSession("PLAN_READY", { id: "session-second", seq: 8 });
    second.transcript = "second transcript";
    let resolveSecond!: (response: Response) => void;
    const slowerSecond = new Promise<Response>((resolve) => { resolveSecond = resolve; });
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const url = String(input);
      if (url.endsWith("/api/config/public")) return json(config);
      if (url.endsWith("/api/sessions")) return json({ sessions: [first, second] });
      if (url.endsWith(`/api/sessions/${first.id}`)) return json({ session: first });
      if (url.endsWith(`/api/sessions/${second.id}`)) return slowerSecond;
      if (url.includes("/events")) return json({ events: [] });
      throw new Error(`unexpected request ${url}`);
    });
    render(<App />);
    expect(await screen.findByText("first transcript")).toBeVisible();

    const historyButtons = screen.getAllByRole("button", { name: /计划待执行/ });
    await userEvent.click(historyButtons[1]);
    await userEvent.click(historyButtons[0]);
    resolveSecond(json({ session: second }));

    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(screen.getByText("first transcript")).toBeVisible();
    expect(screen.queryByText("second transcript")).not.toBeInTheDocument();
  });

  it("opens WebSocket from the 202 snapshot and applies only monotonic critical refreshes", async () => {
    const accepted = makeSession("INPUT_RECEIVED", { seq: 2 });
    const stale = makeSession("INPUT_RECEIVED", { seq: 1 });
    const planned = makeSession("PLAN_READY", { seq: 7 });
    const snapshots = [stale, planned];
    let snapshotReads = 0;
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
      const url = String(input);
      if (url.endsWith("/api/config/public")) return json(config);
      if (url.endsWith("/api/sessions") && (!init?.method || init.method === "GET")) {
        return json({ sessions: [] });
      }
      if (url.endsWith("/api/sessions") && init?.method === "POST") {
        return json({ session_id: accepted.id, session: accepted, transcript_confirmation_required: false }, 202);
      }
      if (url.endsWith(`/api/sessions/${accepted.id}`) && (!init?.method || init.method === "GET")) {
        const snapshot = snapshots[Math.min(snapshotReads, snapshots.length - 1)];
        snapshotReads += 1;
        return json({ session: snapshot });
      }
      throw new Error(`unexpected request ${init?.method ?? "GET"} ${url}`);
    });
    render(<App />);

    await userEvent.click(await screen.findByRole("button", { name: "生成受控计划" }));
    await waitFor(() => expect(ControlledWebSocket.instances).toHaveLength(1));
    expect(screen.getByText("输入已接收")).toBeVisible();

    ControlledWebSocket.instances[0].emit(event("ACTION_COMPLETED", 3));
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(snapshotReads).toBe(0);

    ControlledWebSocket.instances[0].emit(event("PLAN_COMPILED", 4));
    await waitFor(() => expect(snapshotReads).toBe(1));
    expect(screen.getByText("输入已接收")).toBeVisible();

    ControlledWebSocket.instances[0].emit(event("PLAN_COMPILED", 4));
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(snapshotReads).toBe(1);

    ControlledWebSocket.instances[0].emit(event("POLICY_ALLOWED", 7));
    expect(await screen.findByText("计划待执行")).toBeVisible();
  });

  it("rotates a missing challenge once and recovers it from sessionStorage after refresh", async () => {
    const awaiting = makeSession("AWAITING_CONFIRMATION", { seq: 8, confirmation: true });
    const challenge = {
      confirmation_token: "current-tab-token",
      plan_id: "plan-one",
      plan_version: 1,
      expires_at: "2099-07-20T00:05:00Z",
    };
    let challengeCalls = 0;
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const url = String(input);
      if (url.endsWith("/api/config/public")) return json(config);
      if (url.endsWith("/api/sessions")) return json({ sessions: [awaiting] });
      if (url.endsWith(`/api/sessions/${awaiting.id}`)) return json({ session: awaiting });
      if (url.includes("/events")) return json({ events: [] });
      if (url.endsWith("/confirmation-challenge")) {
        challengeCalls += 1;
        return json(challenge);
      }
      throw new Error(`unexpected request ${url}`);
    });

    const first = render(<App />);
    expect(await screen.findByRole("dialog", { name: "写操作确认" })).toBeVisible();
    expect(challengeCalls).toBe(1);
    expect(sessionStorage.getItem(challengeStorageKey(awaiting.id, 1))).toContain("current-tab-token");
    expect(localStorage.length).toBe(0);
    first.unmount();

    render(<App />);
    expect(await screen.findByRole("dialog", { name: "写操作确认" })).toBeVisible();
    expect(challengeCalls).toBe(1);
    expect(localStorage.length).toBe(0);
  });

  it("coalesces duplicate challenge recovery while a rotation is in flight", async () => {
    const awaiting = makeSession("AWAITING_CONFIRMATION", { seq: 8, confirmation: true });
    let resolveChallenge!: (response: Response) => void;
    const pendingChallenge = new Promise<Response>((resolve) => { resolveChallenge = resolve; });
    let challengeCalls = 0;
    let snapshotReads = 0;
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const url = String(input);
      if (url.endsWith("/api/config/public")) return json(config);
      if (url.endsWith("/api/sessions")) return json({ sessions: [awaiting] });
      if (url.endsWith(`/api/sessions/${awaiting.id}`)) {
        snapshotReads += 1;
        return json({ session: awaiting });
      }
      if (url.includes("/events")) return json({ events: [] });
      if (url.endsWith("/confirmation-challenge")) {
        challengeCalls += 1;
        return pendingChallenge;
      }
      throw new Error(`unexpected request ${url}`);
    });
    render(<App />);
    await waitFor(() => expect(ControlledWebSocket.instances).toHaveLength(1));
    await waitFor(() => expect(challengeCalls).toBe(1));

    ControlledWebSocket.instances[0].emit(event("CONFIRMATION_REQUIRED", 9));
    await waitFor(() => expect(snapshotReads).toBe(2));
    expect(challengeCalls).toBe(1);

    resolveChallenge(json({
      confirmation_token: "coalesced-token",
      plan_id: "plan-one",
      plan_version: 1,
      expires_at: "2099-07-20T00:05:00Z",
    }));
    expect(await screen.findByRole("dialog", { name: "写操作确认" })).toBeVisible();
  });

  it("confirms without executing and keeps CONFIRMED retryable after execute HTTP failure", async () => {
    const awaiting = makeSession("AWAITING_CONFIRMATION", { seq: 8, confirmation: true });
    const confirmed = makeSession("CONFIRMED", { seq: 10, confirmation: true });
    const completed = makeSession("COMPLETED", { seq: 15, confirmation: true });
    let confirmCalls = 0;
    let executeCalls = 0;
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
      const url = String(input);
      if (url.endsWith("/api/config/public")) return json(config);
      if (url.endsWith("/api/sessions") && (!init?.method || init.method === "GET")) {
        return json({ sessions: [awaiting] });
      }
      if (url.endsWith(`/api/sessions/${awaiting.id}`) && (!init?.method || init.method === "GET")) {
        return json({ session: awaiting });
      }
      if (url.includes("/events")) return json({ events: [] });
      if (url.endsWith("/confirmation-challenge")) {
        return json({
          confirmation_token: "current-tab-token",
          plan_id: "plan-one",
          plan_version: 1,
          expires_at: "2099-07-20T00:05:00Z",
        });
      }
      if (url.endsWith("/confirm")) {
        confirmCalls += 1;
        return json({ session: confirmed });
      }
      if (url.endsWith("/execute")) {
        executeCalls += 1;
        if (executeCalls === 1) {
          return json({ error: { code: "EXECUTION_PREPARATION_FAILED", message: "retry", retryable: false } }, 500);
        }
        return json({ session: completed });
      }
      throw new Error(`unexpected request ${init?.method ?? "GET"} ${url}`);
    });
    render(<App />);

    await userEvent.click(await screen.findByRole("button", { name: "确认计划" }));
    expect(await screen.findByText("已确认待执行")).toBeVisible();
    expect(confirmCalls).toBe(1);
    expect(executeCalls).toBe(0);

    await userEvent.click(screen.getByRole("button", { name: "执行已确认计划" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("EXECUTION_PREPARATION_FAILED");
    expect(screen.getByRole("button", { name: "执行已确认计划" })).toBeEnabled();

    await userEvent.click(screen.getByRole("button", { name: "执行已确认计划" }));
    expect(await screen.findByText("已完成")).toBeVisible();
    expect(executeCalls).toBe(2);
    expect(sessionStorage.length).toBe(0);
  });

  it("rotates an invalid confirmation token and remains recoverable", async () => {
    const awaiting = makeSession("AWAITING_CONFIRMATION", { seq: 8, confirmation: true });
    const confirmed = makeSession("CONFIRMED", { seq: 10, confirmation: true });
    let challengeCalls = 0;
    const submittedTokens: string[] = [];
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
      const url = String(input);
      if (url.endsWith("/api/config/public")) return json(config);
      if (url.endsWith("/api/sessions") && (!init?.method || init.method === "GET")) {
        return json({ sessions: [awaiting] });
      }
      if (url.endsWith(`/api/sessions/${awaiting.id}`) && (!init?.method || init.method === "GET")) {
        return json({ session: awaiting });
      }
      if (url.includes("/events")) return json({ events: [] });
      if (url.endsWith("/confirmation-challenge")) {
        challengeCalls += 1;
        return json({
          confirmation_token: challengeCalls === 1 ? "stale-token" : "fresh-token",
          plan_id: "plan-one",
          plan_version: 1,
          expires_at: "2099-07-20T00:05:00Z",
        });
      }
      if (url.endsWith("/confirm")) {
        const body = JSON.parse(String(init?.body)) as { confirmation_token: string };
        submittedTokens.push(body.confirmation_token);
        if (submittedTokens.length === 1) {
          return json({
            error: {
              code: "CONFIRMATION_TOKEN_INVALID",
              message: "Confirmation token invalid",
              retryable: false,
            },
          }, 409);
        }
        return json({ session: confirmed });
      }
      throw new Error(`unexpected request ${init?.method ?? "GET"} ${url}`);
    });
    render(<App />);

    await userEvent.click(await screen.findByRole("button", { name: "确认计划" }));
    await waitFor(() => expect(challengeCalls).toBe(2));
    expect(screen.getByRole("alert")).toHaveTextContent("CONFIRMATION_TOKEN_INVALID");
    expect(screen.getByRole("dialog", { name: "写操作确认" })).toBeVisible();

    await userEvent.click(screen.getByRole("button", { name: "确认计划" }));
    expect(await screen.findByText("已确认待执行")).toBeVisible();
    expect(submittedTokens).toEqual(["stale-token", "fresh-token"]);
  });

  it("rejects without execution, clears the challenge, and fully clears UI after delete", async () => {
    const awaiting = makeSession("AWAITING_CONFIRMATION", { seq: 8, confirmation: true });
    const cancelled = makeSession("CANCELLED", { seq: 10, confirmation: true });
    let deleteCalls = 0;
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
      const url = String(input);
      if (url.endsWith("/api/config/public")) return json(config);
      if (url.endsWith("/api/sessions") && (!init?.method || init.method === "GET")) {
        return json({ sessions: deleteCalls ? [] : [cancelled] });
      }
      if (url.endsWith(`/api/sessions/${awaiting.id}`) && init?.method === "DELETE") {
        deleteCalls += 1;
        return new Response(null, { status: 204 });
      }
      if (url.endsWith(`/api/sessions/${awaiting.id}`)) return json({ session: awaiting });
      if (url.includes("/events")) return json({ events: [event("CONFIRMATION_REQUIRED", 8)] });
      if (url.endsWith("/confirmation-challenge")) {
        return json({
          confirmation_token: "current-tab-token",
          plan_id: "plan-one",
          plan_version: 1,
          expires_at: "2099-07-20T00:05:00Z",
        });
      }
      if (url.endsWith("/confirm")) return json({ session: cancelled });
      throw new Error(`unexpected request ${init?.method ?? "GET"} ${url}`);
    });
    render(<App />);

    await userEvent.click(await screen.findByRole("button", { name: "拒绝" }));
    expect((await screen.findAllByText("已取消"))[0]).toBeVisible();
    expect(sessionStorage.length).toBe(0);
    expect(screen.queryByRole("button", { name: "执行已确认计划" })).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "删除 Session" }));
    await waitFor(() => expect(deleteCalls).toBe(1));
    expect(screen.getByText("创建 session 后显示 transcript。")).toBeVisible();
    expect(screen.getByText("事件将按持久化 seq 实时出现。")).toBeVisible();
    expect(screen.getByText("暂无本地 session。")).toBeVisible();
  });
});
