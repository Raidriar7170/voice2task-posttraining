import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  ConfirmationModal,
  ContractPanel,
  Header,
  InputPanel,
  PlanPanel,
  Timeline,
  VerifierPanel,
} from "../components";
import type { ExecutionEvent, SessionRecord } from "../types";

const config = {
  inference_mode: "fixture" as const,
  asr_mode: "disabled" as const,
  execution_mode: "sandbox" as const,
  benchmark_kind: "controlled_fixture_e2e_demo" as const,
};

const session: SessionRecord = {
  id: "session-test",
  created_at: "2026-07-20T00:00:00Z",
  updated_at: "2026-07-20T00:00:01Z",
  status: "AWAITING_CONFIRMATION",
  input_kind: "text",
  context: {
    session_id: "session-test",
    profile: { email: "demo@example.com" },
    selected_capability: "demo_profile_form",
    plan_version: 1,
    plan_issued_at: "2026-07-20T00:00:00Z",
  },
  transcript_original: "把邮箱填进表单里，提交前先问我",
  transcript: "把邮箱填进表单里，提交前先问我",
  transcript_edited: false,
  inference_mode: "fixture",
  asr_mode: "disabled",
  execution_mode: "sandbox",
  contract: {
    task_type: "form_fill",
    route: "fill_form",
    safety: { allow: true, reason: "requires_confirmation" },
    confirmation_required: true,
    slots: { field: "邮箱" },
    normalized_command: "填写邮箱并确认",
    language: "zh-CN",
    contract_version: "v1",
  },
  contract_validation: { strict_schema_valid: true, semantic_valid: true },
  plan: {
    plan_id: "plan-fixture",
    session_id: "session-test",
    plan_version: 1,
    route: "fill_form",
    capability_id: "demo_profile_form",
    requires_confirmation: true,
    actions: [
      {
        action_id: "action-1",
        kind: "navigate",
        capability_id: "demo_profile_form",
        locator_id: null,
        value_source: null,
        timeout_ms: 5000,
      },
      {
        action_id: "action-2",
        kind: "fill",
        capability_id: "demo_profile_form",
        locator_id: "email_input",
        value_source: "session.profile.email",
        timeout_ms: 5000,
      },
    ],
    postconditions: [
      {
        check_type: "field_value_equals",
        capability_id: "demo_profile_form",
        locator_id: "email_input",
        expected_source: "session.profile.email",
      },
    ],
    max_actions: 5,
    expires_at: "2026-07-20T00:05:00Z",
  },
  policy: {
    allowed: false,
    requires_confirmation: true,
    reason_code: "CONFIRMATION_REQUIRED",
    message: "Explicit confirmation is required",
  },
  execution: null,
  verification: {
    passed: true,
    checks: [
      {
        check_type: "field_value_equals",
        passed: true,
        expected: "demo@example.com",
        observed: "demo@example.com",
        evidence_ref: null,
      },
    ],
    failure_code: null,
  },
  error_code: null,
  plan_version: 1,
  confirmation_status: "pending",
  confirmation_plan_id: "plan-fixture",
  confirmation_expires_at: "2026-07-20T00:05:00Z",
  confirmation_consumed_at: null,
  execution_claimed: false,
  cancel_requested: false,
  last_event_seq: 2,
};

const events: ExecutionEvent[] = [
  {
    session_id: "session-test",
    seq: 1,
    event_type: "SESSION_CREATED",
    stage: "session",
    status: "ok",
    message: "Session created",
    payload: {},
    created_at: "2026-07-20T00:00:00Z",
  },
  {
    session_id: "session-test",
    seq: 2,
    event_type: "CONFIRMATION_REQUIRED",
    stage: "confirmation",
    status: "pending",
    message: "Explicit confirmation required",
    payload: { plan_version: 1 },
    created_at: "2026-07-20T00:00:01Z",
  },
];

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe("operation console components", () => {
  it("keeps inference, ASR, and execution modes visibly labeled", () => {
    render(
      <Header
        config={{
          inference_mode: "fixture",
          asr_mode: "disabled",
          execution_mode: "sandbox",
          benchmark_kind: "controlled_fixture_e2e_demo",
        }}
        connectionState="connected"
      />,
    );
    expect(screen.getByText("Fixture Inference")).toBeVisible();
    expect(screen.getByText("ASR Disabled")).toBeVisible();
    expect(screen.getByText("Localhost Sandbox")).toBeVisible();
    expect(screen.getByText(/已连接/)).toBeVisible();
  });

  it("keeps the audio adapter UI inspectable when ASR is disabled", async () => {
    render(
      <InputPanel
        config={{
          inference_mode: "fixture",
          asr_mode: "disabled",
          execution_mode: "sandbox",
          benchmark_kind: "controlled_fixture_e2e_demo",
        }}
        text="帮我搜索北京明天的天气"
        email="demo@example.com"
        inputKind="text"
        audioFile={null}
        busy={false}
        onTextChange={vi.fn()}
        onEmailChange={vi.fn()}
        onInputKindChange={vi.fn()}
        onAudioFile={vi.fn()}
        onError={vi.fn()}
        onSubmit={vi.fn()}
      />,
    );
    expect(screen.getByRole("button", { name: "音频" })).toBeEnabled();
  });

  it("renders contract and plan without exposing selectors or model URLs", () => {
    render(
      <>
        <ContractPanel session={session} />
        <PlanPanel session={session} busy={false} onExecute={vi.fn()} />
      </>,
    );
    expect(screen.getByText("form_fill")).toBeVisible();
    expect(screen.getByText("fill_form")).toBeVisible();
    expect(screen.getByText("demo_profile_form")).toBeVisible();
    expect(screen.getByText("session.profile.email")).toBeVisible();
    expect(screen.getByText("Postconditions")).toBeVisible();
    expect(screen.getByText("field_value_equals")).toBeVisible();
    expect(screen.queryByText(/data-testid/)).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "执行计划" })).not.toBeInTheDocument();
  });

  it("shows explicit transient status text and separate confirmed execution controls", () => {
    const execute = vi.fn();
    const cancel = vi.fn();
    const deleteSession = vi.fn();
    const { rerender } = render(
      <PlanPanel
        session={{ ...session, status: "TRANSCRIBING" }}
        busy={false}
        onExecute={execute}
        onCancel={cancel}
        onDelete={deleteSession}
      />,
    );
    expect(screen.getByText("正在转写")).toBeVisible();

    rerender(
      <PlanPanel
        session={{ ...session, status: "CONFIRMED" }}
        busy={false}
        onExecute={execute}
        onCancel={cancel}
        onDelete={deleteSession}
      />,
    );
    expect(screen.getByText("已确认待执行")).toBeVisible();
    expect(screen.getByRole("button", { name: "执行已确认计划" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "取消 Session" })).toBeEnabled();

    rerender(
      <PlanPanel
        session={{ ...session, status: "COMPLETED" }}
        busy={false}
        onExecute={execute}
        onCancel={cancel}
        onDelete={deleteSession}
      />,
    );
    expect(screen.getByRole("button", { name: "删除 Session" })).toBeEnabled();
    expect(screen.queryByRole("button", { name: "执行已确认计划" })).not.toBeInTheDocument();
  });

  it("keeps cancel and delete controls available before a plan exists", () => {
    const cancel = vi.fn();
    const deleteSession = vi.fn();
    const withoutPlan = { ...session, plan: null, contract: null, policy: null };
    const { rerender } = render(
      <PlanPanel
        session={{ ...withoutPlan, status: "INPUT_RECEIVED" }}
        busy={false}
        onExecute={vi.fn()}
        onCancel={cancel}
        onDelete={deleteSession}
      />,
    );
    expect(screen.getByRole("button", { name: "取消 Session" })).toBeEnabled();

    rerender(
      <PlanPanel
        session={{ ...withoutPlan, status: "FAILED" }}
        busy={false}
        onExecute={vi.fn()}
        onCancel={cancel}
        onDelete={deleteSession}
      />,
    );
    expect(screen.getByRole("button", { name: "删除 Session" })).toBeEnabled();
  });

  it("shows explicit confirmation details and handles approve/reject", async () => {
    const approve = vi.fn();
    const reject = vi.fn();
    render(
      <ConfirmationModal
        session={session}
        open
        busy={false}
        onApprove={approve}
        onReject={reject}
      />,
    );
    expect(screen.getByRole("dialog", { name: "写操作确认" })).toBeVisible();
    expect(screen.getByText(/不访问真实网站/)).toBeVisible();
    await userEvent.click(screen.getByRole("button", { name: "确认计划" }));
    await userEvent.click(screen.getByRole("button", { name: "拒绝" }));
    expect(approve).toHaveBeenCalledOnce();
    expect(reject).toHaveBeenCalledOnce();
  });

  it("reports unsupported microphone access without an unhandled rejection", async () => {
    const onError = vi.fn();
    Object.defineProperty(navigator, "mediaDevices", { configurable: true, value: undefined });
    render(
      <InputPanel
        config={{ ...config, asr_mode: "fixture" }}
        text=""
        email="demo@example.com"
        inputKind="audio"
        audioFile={null}
        busy={false}
        onTextChange={vi.fn()}
        onEmailChange={vi.fn()}
        onInputKindChange={vi.fn()}
        onAudioFile={vi.fn()}
        onError={onError}
        onSubmit={vi.fn()}
      />,
    );

    await userEvent.click(screen.getByRole("button", { name: "开始录音" }));
    await waitFor(() => expect(onError).toHaveBeenCalledWith(
      "MICROPHONE_UNSUPPORTED",
      expect.any(String),
    ));
  });

  it("reports microphone permission denial without leaking a rejection", async () => {
    const onError = vi.fn();
    Object.defineProperty(navigator, "mediaDevices", {
      configurable: true,
      value: {
        getUserMedia: vi.fn().mockRejectedValue(
          new DOMException("permission denied", "NotAllowedError"),
        ),
      },
    });
    vi.stubGlobal("MediaRecorder", class {});
    render(
      <InputPanel
        config={{ ...config, asr_mode: "fixture" }}
        text=""
        email="demo@example.com"
        inputKind="audio"
        audioFile={null}
        busy={false}
        onTextChange={vi.fn()}
        onEmailChange={vi.fn()}
        onInputKindChange={vi.fn()}
        onAudioFile={vi.fn()}
        onError={onError}
        onSubmit={vi.fn()}
      />,
    );

    await userEvent.click(screen.getByRole("button", { name: "开始录音" }));
    await waitFor(() => expect(onError).toHaveBeenCalledWith(
      "MICROPHONE_PERMISSION_DENIED",
      expect.any(String),
    ));
  });

  it("stops acquired tracks when MediaRecorder construction fails", async () => {
    const stop = vi.fn();
    const onError = vi.fn();
    Object.defineProperty(navigator, "mediaDevices", {
      configurable: true,
      value: { getUserMedia: vi.fn().mockResolvedValue({ getTracks: () => [{ stop }] }) },
    });
    vi.stubGlobal("MediaRecorder", class {
      constructor() { throw new Error("constructor failed"); }
    });
    render(
      <InputPanel
        config={{ ...config, asr_mode: "fixture" }}
        text=""
        email="demo@example.com"
        inputKind="audio"
        audioFile={null}
        busy={false}
        onTextChange={vi.fn()}
        onEmailChange={vi.fn()}
        onInputKindChange={vi.fn()}
        onAudioFile={vi.fn()}
        onError={onError}
        onSubmit={vi.fn()}
      />,
    );

    await userEvent.click(screen.getByRole("button", { name: "开始录音" }));
    await waitFor(() => expect(onError).toHaveBeenCalledWith(
      "MICROPHONE_START_FAILED",
      expect.any(String),
    ));
    expect(stop).toHaveBeenCalledOnce();
  });

  it("stops every acquired track when MediaRecorder.start fails", async () => {
    const stop = vi.fn();
    const onError = vi.fn();
    Object.defineProperty(navigator, "mediaDevices", {
      configurable: true,
      value: { getUserMedia: vi.fn().mockResolvedValue({ getTracks: () => [{ stop }] }) },
    });
    vi.stubGlobal("MediaRecorder", class {
      start() { throw new Error("start failed"); }
      stop() {}
    });
    render(
      <InputPanel
        config={{ ...config, asr_mode: "fixture" }}
        text=""
        email="demo@example.com"
        inputKind="audio"
        audioFile={null}
        busy={false}
        onTextChange={vi.fn()}
        onEmailChange={vi.fn()}
        onInputKindChange={vi.fn()}
        onAudioFile={vi.fn()}
        onError={onError}
        onSubmit={vi.fn()}
      />,
    );

    await userEvent.click(screen.getByRole("button", { name: "开始录音" }));
    await waitFor(() => expect(onError).toHaveBeenCalledWith(
      "MICROPHONE_START_FAILED",
      expect.any(String),
    ));
    expect(stop).toHaveBeenCalledOnce();
  });

  it("stops every active microphone track on unmount", async () => {
    const stop = vi.fn();
    Object.defineProperty(navigator, "mediaDevices", {
      configurable: true,
      value: { getUserMedia: vi.fn().mockResolvedValue({ getTracks: () => [{ stop }] }) },
    });
    vi.stubGlobal("MediaRecorder", class {
      ondataavailable: ((event: BlobEvent) => void) | null = null;
      onstop: (() => void) | null = null;
      onerror: (() => void) | null = null;
      start() {}
      stop() { this.onstop?.(); }
    });
    const { unmount } = render(
      <InputPanel
        config={{ ...config, asr_mode: "fixture" }}
        text=""
        email="demo@example.com"
        inputKind="audio"
        audioFile={null}
        busy={false}
        onTextChange={vi.fn()}
        onEmailChange={vi.fn()}
        onInputKindChange={vi.fn()}
        onAudioFile={vi.fn()}
        onError={vi.fn()}
        onSubmit={vi.fn()}
      />,
    );
    await userEvent.click(screen.getByRole("button", { name: "开始录音" }));

    unmount();
    expect(stop).toHaveBeenCalledOnce();
  });

  it("stops active tracks on recorder error", async () => {
    const stop = vi.fn();
    const onError = vi.fn();
    let instance: { onerror: (() => void) | null } | null = null;
    Object.defineProperty(navigator, "mediaDevices", {
      configurable: true,
      value: { getUserMedia: vi.fn().mockResolvedValue({ getTracks: () => [{ stop }] }) },
    });
    vi.stubGlobal("MediaRecorder", class {
      state = "recording";
      ondataavailable: ((event: BlobEvent) => void) | null = null;
      onstop: (() => void) | null = null;
      onerror: (() => void) | null = null;
      constructor() { instance = this; }
      start() {}
      stop() {}
    });
    render(
      <InputPanel
        config={{ ...config, asr_mode: "fixture" }}
        text=""
        email="demo@example.com"
        inputKind="audio"
        audioFile={null}
        busy={false}
        onTextChange={vi.fn()}
        onEmailChange={vi.fn()}
        onInputKindChange={vi.fn()}
        onAudioFile={vi.fn()}
        onError={onError}
        onSubmit={vi.fn()}
      />,
    );
    await userEvent.click(screen.getByRole("button", { name: "开始录音" }));

    act(() => instance?.onerror?.());
    expect(onError).toHaveBeenCalledWith("MICROPHONE_RECORDING_FAILED", expect.any(String));
    expect(stop).toHaveBeenCalledOnce();
  });

  it("stops active tracks when switching away from audio input", async () => {
    const stop = vi.fn();
    Object.defineProperty(navigator, "mediaDevices", {
      configurable: true,
      value: { getUserMedia: vi.fn().mockResolvedValue({ getTracks: () => [{ stop }] }) },
    });
    vi.stubGlobal("MediaRecorder", class {
      state = "recording";
      ondataavailable: ((event: BlobEvent) => void) | null = null;
      onstop: (() => void) | null = null;
      onerror: (() => void) | null = null;
      start() {}
      stop() { this.onstop?.(); }
    });
    const common = {
      config: { ...config, asr_mode: "fixture" as const },
      text: "",
      email: "demo@example.com",
      audioFile: null,
      busy: false,
      onTextChange: vi.fn(),
      onEmailChange: vi.fn(),
      onInputKindChange: vi.fn(),
      onAudioFile: vi.fn(),
      onError: vi.fn(),
      onSubmit: vi.fn(),
    };
    const view = render(<InputPanel {...common} inputKind="audio" />);
    await userEvent.click(screen.getByRole("button", { name: "开始录音" }));

    view.rerender(<InputPanel {...common} inputKind="text" />);
    expect(stop).toHaveBeenCalledOnce();
  });

  it("discards a microphone stream acquired after switching to text", async () => {
    const stop = vi.fn();
    const constructRecorder = vi.fn();
    let resolveAcquisition!: (stream: MediaStream) => void;
    const pending = new Promise<MediaStream>((resolve) => {
      resolveAcquisition = resolve;
    });
    Object.defineProperty(navigator, "mediaDevices", {
      configurable: true,
      value: { getUserMedia: vi.fn().mockReturnValue(pending) },
    });
    vi.stubGlobal("MediaRecorder", class {
      constructor() { constructRecorder(); }
      start() {}
      stop() {}
    });
    const common = {
      config: { ...config, asr_mode: "fixture" as const },
      text: "",
      email: "demo@example.com",
      audioFile: null,
      busy: false,
      onTextChange: vi.fn(),
      onEmailChange: vi.fn(),
      onInputKindChange: vi.fn(),
      onAudioFile: vi.fn(),
      onError: vi.fn(),
      onSubmit: vi.fn(),
    };
    const view = render(<InputPanel {...common} inputKind="audio" />);
    await userEvent.click(screen.getByRole("button", { name: "开始录音" }));

    view.rerender(<InputPanel {...common} inputKind="text" />);
    resolveAcquisition({ getTracks: () => [{ stop }] } as unknown as MediaStream);

    await waitFor(() => expect(stop).toHaveBeenCalledOnce());
    expect(constructRecorder).not.toHaveBeenCalled();
  });

  it("coalesces repeated microphone clicks while acquisition is pending", async () => {
    const getUserMedia = vi.fn().mockReturnValue(new Promise<MediaStream>(() => undefined));
    Object.defineProperty(navigator, "mediaDevices", {
      configurable: true,
      value: { getUserMedia },
    });
    vi.stubGlobal("MediaRecorder", class {});
    render(
      <InputPanel
        config={{ ...config, asr_mode: "fixture" }}
        text=""
        email="demo@example.com"
        inputKind="audio"
        audioFile={null}
        busy={false}
        onTextChange={vi.fn()}
        onEmailChange={vi.fn()}
        onInputKindChange={vi.fn()}
        onAudioFile={vi.fn()}
        onError={vi.fn()}
        onSubmit={vi.fn()}
      />,
    );
    const start = screen.getByRole("button", { name: "开始录音" });

    await userEvent.click(start);
    await userEvent.click(start);

    expect(getUserMedia).toHaveBeenCalledOnce();
  });

  it("stops a microphone stream acquired after unmount", async () => {
    const stop = vi.fn();
    let resolveAcquisition!: (stream: MediaStream) => void;
    const pending = new Promise<MediaStream>((resolve) => {
      resolveAcquisition = resolve;
    });
    Object.defineProperty(navigator, "mediaDevices", {
      configurable: true,
      value: { getUserMedia: vi.fn().mockReturnValue(pending) },
    });
    vi.stubGlobal("MediaRecorder", class {});
    const { unmount } = render(
      <InputPanel
        config={{ ...config, asr_mode: "fixture" }}
        text=""
        email="demo@example.com"
        inputKind="audio"
        audioFile={null}
        busy={false}
        onTextChange={vi.fn()}
        onEmailChange={vi.fn()}
        onInputKindChange={vi.fn()}
        onAudioFile={vi.fn()}
        onError={vi.fn()}
        onSubmit={vi.fn()}
      />,
    );
    await userEvent.click(screen.getByRole("button", { name: "开始录音" }));

    unmount();
    resolveAcquisition({ getTracks: () => [{ stop }] } as unknown as MediaStream);

    await waitFor(() => expect(stop).toHaveBeenCalledOnce());
  });

  it("stops active tracks before replacing a recording with an uploaded file", async () => {
    const stop = vi.fn();
    const onAudioFile = vi.fn();
    Object.defineProperty(navigator, "mediaDevices", {
      configurable: true,
      value: { getUserMedia: vi.fn().mockResolvedValue({ getTracks: () => [{ stop }] }) },
    });
    vi.stubGlobal("MediaRecorder", class {
      state = "recording";
      ondataavailable: ((event: BlobEvent) => void) | null = null;
      onstop: (() => void) | null = null;
      onerror: (() => void) | null = null;
      start() {}
      stop() { this.onstop?.(); }
    });
    const { container } = render(
      <InputPanel
        config={{ ...config, asr_mode: "fixture" }}
        text=""
        email="demo@example.com"
        inputKind="audio"
        audioFile={null}
        busy={false}
        onTextChange={vi.fn()}
        onEmailChange={vi.fn()}
        onInputKindChange={vi.fn()}
        onAudioFile={onAudioFile}
        onError={vi.fn()}
        onSubmit={vi.fn()}
      />,
    );
    await userEvent.click(screen.getByRole("button", { name: "开始录音" }));

    const replacement = new File(["audio"], "replacement.webm", { type: "audio/webm" });
    fireEvent.change(container.querySelector('input[type="file"]') as HTMLInputElement, {
      target: { files: [replacement] },
    });
    expect(stop).toHaveBeenCalledOnce();
    expect(onAudioFile).toHaveBeenCalledWith(replacement);
  });

  it("does not let a delayed recorder stop overwrite an uploaded replacement", async () => {
    const stop = vi.fn();
    const onAudioFile = vi.fn();
    let instance: {
      ondataavailable: ((event: BlobEvent) => void) | null;
      onstop: (() => void) | null;
    } | null = null;
    Object.defineProperty(navigator, "mediaDevices", {
      configurable: true,
      value: { getUserMedia: vi.fn().mockResolvedValue({ getTracks: () => [{ stop }] }) },
    });
    vi.stubGlobal("MediaRecorder", class {
      state = "recording";
      ondataavailable: ((event: BlobEvent) => void) | null = null;
      onstop: (() => void) | null = null;
      onerror: (() => void) | null = null;
      constructor() { instance = this; }
      start() {
        this.ondataavailable?.({ data: new Blob(["old-recording"]) } as BlobEvent);
      }
      stop() {}
    });
    const { container } = render(
      <InputPanel
        config={{ ...config, asr_mode: "fixture" }}
        text=""
        email="demo@example.com"
        inputKind="audio"
        audioFile={null}
        busy={false}
        onTextChange={vi.fn()}
        onEmailChange={vi.fn()}
        onInputKindChange={vi.fn()}
        onAudioFile={onAudioFile}
        onError={vi.fn()}
        onSubmit={vi.fn()}
      />,
    );
    await userEvent.click(screen.getByRole("button", { name: "开始录音" }));
    const replacement = new File(["replacement"], "replacement.webm", { type: "audio/webm" });
    fireEvent.change(container.querySelector('input[type="file"]') as HTMLInputElement, {
      target: { files: [replacement] },
    });

    act(() => instance?.onstop?.());

    expect(stop).toHaveBeenCalledOnce();
    expect(onAudioFile).toHaveBeenCalledOnce();
    expect(onAudioFile).toHaveBeenLastCalledWith(replacement);
  });

  it("renders sequenced timeline and verifier pass text independent of color", () => {
    render(
      <>
        <Timeline events={events} connectionState="reconnecting" />
        <VerifierPanel session={session} />
      </>,
    );
    expect(screen.getByText("#1")).toBeVisible();
    expect(screen.getByText("#2")).toBeVisible();
    expect(screen.getByText("正在重连事件流")).toBeVisible();
    expect(screen.getByText("通过")).toBeVisible();
    expect(screen.getByText("demo@example.com", { exact: true })).toBeVisible();
  });
});
