import { useEffect, useRef, useState } from "react";

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
import {
  loadMatchingChallenge,
  removeSessionChallenges,
  saveChallenge,
} from "./lib/confirmationChallenge";
import type {
  ConfirmationChallenge,
  ExecutionEvent,
  PublicConfig,
  SessionRecord,
} from "./types";

const DEFAULT_CONFIG: PublicConfig = {
  inference_mode: "fixture",
  asr_mode: "disabled",
  execution_mode: "sandbox",
  benchmark_kind: "controlled_fixture_e2e_demo",
};

const TERMINAL_STATUSES = new Set([
  "COMPLETED",
  "BLOCKED",
  "CLARIFICATION_REQUIRED",
  "FAILED",
  "CANCELLED",
]);

const ROTATABLE_CONFIRMATION_ERRORS = new Set([
  "CONFIRMATION_TOKEN_INVALID",
  "CONFIRMATION_EXPIRED",
  "CONFIRMATION_BINDING_MISMATCH",
]);

function describeError(error: unknown): { code: string; message: string } {
  if (error instanceof DemoAPIError) return { code: error.code, message: error.message };
  return { code: "CLIENT_ERROR", message: "请求失败；受控 Demo 未执行任何 fallback。" };
}

export default function App() {
  const [config, setConfig] = useState<PublicConfig>(DEFAULT_CONFIG);
  const [sessions, setSessions] = useState<SessionRecord[]>([]);
  const [session, setSession] = useState<SessionRecord | null>(null);
  const [challenge, setChallenge] = useState<ConfirmationChallenge | null>(null);
  const [inputKind, setInputKind] = useState<"text" | "audio">("text");
  const [text, setText] = useState("帮我搜索北京明天的天气");
  const [email, setEmail] = useState("demo@example.com");
  const [audioFile, setAudioFile] = useState<File | null>(null);
  const [transcript, setTranscript] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<{ code: string; message: string } | null>(null);
  const activeSessionId = useRef<string | null>(null);
  const currentSession = useRef<SessionRecord | null>(null);
  const selectionGeneration = useRef(0);
  const challengeRequests = useRef(new Map<string, Promise<ConfirmationChallenge>>());

  const refreshHistory = async () => {
    const response = await api.sessions();
    setSessions(response.sessions);
    return response.sessions;
  };

  const clearChallenge = (sessionId: string) => {
    removeSessionChallenges(sessionStorage, sessionId);
    if (activeSessionId.current === sessionId) setChallenge(null);
  };

  const recoverChallenge = async (record: SessionRecord, generation: number) => {
    if (record.status !== "AWAITING_CONFIRMATION" || !record.plan) {
      clearChallenge(record.id);
      return;
    }
    const stored = loadMatchingChallenge(sessionStorage, record);
    if (stored) {
      if (selectionGeneration.current === generation && activeSessionId.current === record.id) {
        setChallenge(stored);
      }
      return;
    }
    const requestKey = `${record.id}:${record.plan_version}:${record.plan.plan_id}`;
    let request = challengeRequests.current.get(requestKey);
    if (!request) {
      request = api.confirmationChallenge(record.id);
      challengeRequests.current.set(requestKey, request);
      void request.finally(() => {
        if (challengeRequests.current.get(requestKey) === request) {
          challengeRequests.current.delete(requestKey);
        }
      }).catch(() => undefined);
    }
    const rotated = await request;
    const latest = currentSession.current;
    if (
      selectionGeneration.current !== generation
      || activeSessionId.current !== record.id
      || latest?.status !== "AWAITING_CONFIRMATION"
      || latest.plan?.plan_id !== rotated.plan_id
      || latest.plan_version !== rotated.plan_version
    ) return;
    saveChallenge(sessionStorage, record.id, rotated);
    setChallenge(rotated);
  };

  const applySnapshot = (record: SessionRecord, generation: number): boolean => {
    if (selectionGeneration.current !== generation || activeSessionId.current !== record.id) {
      return false;
    }
    const previous = currentSession.current;
    if (previous?.id === record.id && record.last_event_seq < previous.last_event_seq) {
      return false;
    }
    currentSession.current = record;
    setSession(record);
    setTranscript(record.transcript ?? "");
    return true;
  };

  const settleSnapshot = async (record: SessionRecord, generation: number) => {
    if (!applySnapshot(record, generation)) return;
    await recoverChallenge(record, generation);
    if (TERMINAL_STATUSES.has(record.status)) await refreshHistory();
  };

  const loadSession = async (sessionId: string) => {
    const generation = selectionGeneration.current + 1;
    selectionGeneration.current = generation;
    activeSessionId.current = sessionId;
    currentSession.current = null;
    setChallenge(null);
    let [record, replay] = await Promise.all([api.session(sessionId), api.events(sessionId)]);
    const replayLastSequence = replay.events.reduce(
      (highest, event) => Math.max(highest, event.seq),
      0,
    );
    if (replayLastSequence > record.session.last_event_seq) {
      record = await api.session(sessionId);
    }
    if (!applySnapshot(record.session, generation)) return;
    replaceEvents(sessionId, replay.events);
    await recoverChallenge(record.session, generation);
  };

  const handleSnapshotSignal = (event: ExecutionEvent) => {
    const generation = selectionGeneration.current;
    if (activeSessionId.current !== event.session_id) return;
    void api.session(event.session_id)
      .then((response) => settleSnapshot(response.session, generation))
      .catch((caught) => {
        if (selectionGeneration.current === generation && activeSessionId.current === event.session_id) {
          setError(describeError(caught));
        }
      });
  };

  const { events, setEvents, replaceEvents, connectionState } = useSessionEvents(
    session?.id ?? null,
    handleSnapshotSignal,
  );

  useEffect(() => {
    let disposed = false;
    void Promise.all([api.config(), api.sessions()])
      .then(async ([publicConfig, history]) => {
        if (disposed) return;
        setConfig(publicConfig);
        setSessions(history.sessions);
        if (history.sessions.length > 0) await loadSession(history.sessions[0].id);
      })
      .catch((caught) => {
        if (!disposed) setError(describeError(caught));
      });
    return () => {
      disposed = true;
      selectionGeneration.current += 1;
      activeSessionId.current = null;
      currentSession.current = null;
    };
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
    const generation = selectionGeneration.current + 1;
    selectionGeneration.current = generation;
    activeSessionId.current = response.session.id;
    currentSession.current = response.session;
    setSession(response.session);
    setChallenge(null);
    setEvents([]);
    setTranscript(response.session.transcript ?? "");
    await recoverChallenge(response.session, generation);
    await refreshHistory();
  });

  const confirmTranscript = () => {
    if (!session) return;
    const generation = selectionGeneration.current;
    void run(async () => {
      const response = await api.confirmTranscript(session.id, transcript, session.plan_version);
      await settleSnapshot(response.session, generation);
      await refreshHistory();
    });
  };

  const execute = () => {
    if (!session) return;
    const generation = selectionGeneration.current;
    void run(async () => {
      const response = await api.execute(session.id);
      await settleSnapshot(response.session, generation);
      if (!TERMINAL_STATUSES.has(response.session.status)) await refreshHistory();
    });
  };

  const approve = () => {
    if (!session || !challenge) return;
    const generation = selectionGeneration.current;
    void run(async () => {
      let response;
      try {
        response = await api.confirm(
          session.id,
          "approve",
          challenge.plan_version,
          challenge.confirmation_token,
        );
      } catch (caught) {
        if (caught instanceof DemoAPIError && ROTATABLE_CONFIRMATION_ERRORS.has(caught.code)) {
          clearChallenge(session.id);
          const latest = currentSession.current;
          if (latest?.id === session.id && latest.status === "AWAITING_CONFIRMATION") {
            try {
              await recoverChallenge(latest, generation);
            } catch {
              // The original stable API error remains the user-visible failure.
            }
          }
        }
        throw caught;
      }
      clearChallenge(session.id);
      await settleSnapshot(response.session, generation);
      await refreshHistory();
    });
  };

  const reject = () => {
    if (!session || !challenge) return;
    const generation = selectionGeneration.current;
    void run(async () => {
      let response;
      try {
        response = await api.confirm(
          session.id,
          "reject",
          challenge.plan_version,
          challenge.confirmation_token,
        );
      } catch (caught) {
        if (caught instanceof DemoAPIError && ROTATABLE_CONFIRMATION_ERRORS.has(caught.code)) {
          clearChallenge(session.id);
          const latest = currentSession.current;
          if (latest?.id === session.id && latest.status === "AWAITING_CONFIRMATION") {
            try {
              await recoverChallenge(latest, generation);
            } catch {
              // The original stable API error remains the user-visible failure.
            }
          }
        }
        throw caught;
      }
      clearChallenge(session.id);
      await settleSnapshot(response.session, generation);
    });
  };

  const cancel = () => {
    if (!session) return;
    const generation = selectionGeneration.current;
    void run(async () => {
      const response = await api.cancel(session.id);
      clearChallenge(session.id);
      await settleSnapshot(response.session, generation);
    });
  };

  const deleteSession = () => {
    if (!session) return;
    const sessionId = session.id;
    void run(async () => {
      await api.deleteSession(sessionId);
      clearChallenge(sessionId);
      selectionGeneration.current += 1;
      activeSessionId.current = null;
      currentSession.current = null;
      setSession(null);
      setTranscript("");
      setEvents([]);
      setSessions((current) => current.filter((item) => item.id !== sessionId));
    });
  };

  const selectSession = (sessionId: string) => {
    void run(() => loadSession(sessionId));
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
            onError={(code, message) => setError({ code, message })}
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
          <PlanPanel
            session={session}
            busy={busy}
            onExecute={execute}
            onCancel={cancel}
            onDelete={deleteSession}
          />
        </div>
        <div className="console-column">
          <Timeline events={events} connectionState={connectionState} />
          <VerifierPanel session={session} />
          <SessionHistory sessions={sessions} selectedId={session?.id ?? null} onSelect={selectSession} />
        </div>
      </main>
      <div className="retention-disclosure">
        Session、事件和截图仅保存在本机 SQLite / var/demo；删除 Session 会删除对应记录和截图。原始音频仅临时存放；confirmation challenge 仅保存在当前 tab 的 sessionStorage，不使用 localStorage。
      </div>
      <footer>
        <span>Voice2Task · BrowserTaskContract V1</span>
        <span>No arbitrary URL · No selector injection · No external execution</span>
      </footer>
      {session && (
        <ConfirmationModal
          session={session}
          open={session.status === "AWAITING_CONFIRMATION" && Boolean(challenge)}
          busy={busy}
          onApprove={approve}
          onReject={reject}
        />
      )}
    </div>
  );
}
