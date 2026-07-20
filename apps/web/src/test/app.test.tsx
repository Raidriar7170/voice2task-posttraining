import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import App from "../App";

class MockWebSocket {
  static OPEN = 1;
  readyState = 1;
  onopen: (() => void) | null = null;
  onmessage: ((event: MessageEvent<string>) => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: (() => void) | null = null;
  constructor(_url: string) {
    setTimeout(() => this.onopen?.(), 0);
  }
  close() {
    this.onclose?.();
  }
}

const config = {
  inference_mode: "fixture",
  asr_mode: "disabled",
  execution_mode: "sandbox",
  benchmark_kind: "controlled_fixture_e2e_demo",
};

afterEach(() => {
  vi.restoreAllMocks();
});

describe("App", () => {
  it("renders input, history, mode boundaries, and a readable API error", async () => {
    vi.stubGlobal("WebSocket", MockWebSocket);
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
      const url = String(input);
      if (url.endsWith("/api/config/public")) {
        return new Response(JSON.stringify(config), { status: 200 });
      }
      if (url.endsWith("/api/sessions") && (!init?.method || init.method === "GET")) {
        return new Response(JSON.stringify({ sessions: [] }), { status: 200 });
      }
      return new Response(
        JSON.stringify({
          error: { code: "FIXTURE_INPUT_UNSUPPORTED", message: "仅支持六条演示指令", retryable: false },
        }),
        { status: 422 },
      );
    });
    render(<App />);

    expect(await screen.findByText("Fixture Inference")).toBeVisible();
    expect(screen.getByRole("heading", { name: "输入" })).toBeVisible();
    expect(screen.getByRole("heading", { name: "Session History" })).toBeVisible();
    expect(screen.getByText(/受控 fixture/)).toBeVisible();

    await userEvent.clear(screen.getByLabelText("中文指令"));
    await userEvent.type(screen.getByLabelText("中文指令"), "任意输入");
    await userEvent.click(screen.getByRole("button", { name: "生成受控计划" }));
    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("仅支持六条演示指令"));
    expect(screen.getByRole("alert")).toHaveTextContent("FIXTURE_INPUT_UNSUPPORTED");
  });
});
