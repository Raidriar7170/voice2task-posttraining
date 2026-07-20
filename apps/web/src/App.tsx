import { useEffect, useState } from "react";

import {
  ConfirmationModal,
  ContractPanel,
  Header,
  InputPanel,
  PlanPanel,
  SessionHistory,
  Timeline,
  TranscriptPanel,
  VerifierPanel,
} from "./components";
import { useSessionEvents } from "./hooks/useSessionEvents";
import { api, DemoAPIError } from "./lib/api";
import type { PublicConfig, SessionRecord } from "./types";

const DEFAULT_CONFIG: PublicConfig = {
  inference_mode: "fixture",
  asr_mode: "disabled",
  execution_mode: "sandbox",
  benchmark_kind: "controlled_fixture_e2e_demo",
};

function describeError(error: unknown): { code: string; message: string } {
  if (error instanceof DemoAPIError) return { code: error.code, message: error.message };
  return { code: "CLIENT_ERROR", message: "请求失败；受控 Demo 未执行任何 fallback。" };
}

export default function App() {
  const [config, setConfig] = useState<PublicConfig>(DEFAULT_CONFIG);
  const [sessions, setSessions] = useState<SessionRecord[]>([]);
  const [session, setSession] = useState<SessionRecord | null>(null);
  const [confirmationToken, setConfirmationToken] = useState<string | null>(null);
  const [inputKind, setInputKind] = useState<"text" | "audio">("text");
  const [text, setText] = useState("帮我搜索北京明天的天气");
  const [email, setEmail] = useState("demo@example.com");
  const [audioFile, setAudioFile] = useState<File | null>(null);
  const [transcript, setTranscript] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<{ code: string; message: string } | null>(null);
  const { events, setEvents, connectionState } = useSessionEvents(session?.id ?? null);

  const refreshHistory = async () => {
    const response = await api.sessions();
    setSessions(response.sessions);
  };

  useEffect(() => {
    void Promise.all([api.config(), api.sessions()])
      .then(([publicConfig, history]) => {
        setConfig(publicConfig);
        setSessions(history.sessions);
      })
      .catch((caught) => setError(describeError(caught)));
  }, []);

  const run = async (operation: () => Promise<void>) => {
    setBusy(true);
    setError(null);
    try {
      await operation();
    } catch (caught) {
      setError(describeError(caught));
    } finally {
      setBusy(false);
    }
  };

  const submit = () => run(async () => {
    const response = inputKind === "text"
      ? await api.createText(text, email)
      : await api.createAudio(
        audioFile as File,
        email,
        config.asr_mode === "fixture" ? "fixture-search" : undefined,
      );
    setSession(response.session);
    setConfirmationToken(response.confirmation_token);
    setTranscript(response.session.transcript ?? "");
    await refreshHistory();
  });

  const confirmTranscript = () => {
    if (!session) return;
    void run(async () => {
      const response = await api.confirmTranscript(session.id, transcript, session.plan_version);
      setSession(response.session);
      setConfirmationToken(response.confirmation_token);
      await refreshHistory();
    });
  };

  const execute = () => {
    if (!session) return;
    void run(async () => {
      const response = await api.execute(session.id);
      setSession(response.session);
      await refreshHistory();
    });
  };

  const approve = () => {
    if (!session || !confirmationToken) return;
    void run(async () => {
      const confirmed = await api.confirm(
        session.id,
        "approve",
        session.plan_version,
        confirmationToken,
      );
      setSession(confirmed.session);
      const executed = await api.execute(session.id);
      setSession(executed.session);
      setConfirmationToken(null);
      await refreshHistory();
    });
  };

  const reject = () => {
    if (!session || !confirmationToken) return;
    void run(async () => {
      const response = await api.confirm(
        session.id,
        "reject",
        session.plan_version,
        confirmationToken,
      );
      setSession(response.session);
      setConfirmationToken(null);
      await refreshHistory();
    });
  };

  const selectSession = (sessionId: string) => {
    void run(async () => {
      const [record, replay] = await Promise.all([api.session(sessionId), api.events(sessionId)]);
      setSession(record.session);
      setTranscript(record.session.transcript ?? "");
      setConfirmationToken(null);
      setEvents(replay.events);
    });
  };

  return (
    <div className="app-shell">
      <Header config={config} connectionState={connectionState} />
      <div className="truth-banner">
        <strong>CONTROLLED FIXTURE E2E DEMO</strong>
        <span>只证明 localhost 受控 fixture 编排；不证明模型质量、自然语音或互联网泛化。</span>
      </div>
      {error && (
        <div className="error-banner" role="alert">
          <strong>{error.code}</strong><span>{error.message}</span>
        </div>
      )}
      <main className="console-grid">
        <div className="console-column">
          <InputPanel
            config={config}
            text={text}
            email={email}
            inputKind={inputKind}
            audioFile={audioFile}
            busy={busy}
            onTextChange={setText}
            onEmailChange={setEmail}
            onInputKindChange={setInputKind}
            onAudioFile={setAudioFile}
            onSubmit={() => void submit()}
          />
          <TranscriptPanel
            session={session}
            transcript={transcript}
            busy={busy}
            onChange={setTranscript}
            onConfirm={confirmTranscript}
          />
          <ContractPanel session={session} />
          <PlanPanel session={session} busy={busy} onExecute={execute} />
        </div>
        <div className="console-column">
          <Timeline events={events} connectionState={connectionState} />
          <VerifierPanel session={session} />
          <SessionHistory sessions={sessions} selectedId={session?.id ?? null} onSelect={selectSession} />
        </div>
      </main>
      <footer>
        <span>Voice2Task · BrowserTaskContract V1</span>
        <span>No arbitrary URL · No selector injection · No external execution</span>
      </footer>
      {session && (
        <ConfirmationModal
          session={session}
          open={session.status === "AWAITING_CONFIRMATION" && Boolean(confirmationToken)}
          busy={busy}
          onApprove={approve}
          onReject={reject}
        />
      )}
    </div>
  );
}
