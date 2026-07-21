import { useCallback, useEffect, useRef, useState } from "react";

import type {
  ConnectionState,
  ExecutionEvent,
  PublicConfig,
  SessionRecord,
} from "../types";

const STATUS_LABELS: Record<string, string> = {
  CREATED: "正在创建 Session",
  INPUT_RECEIVED: "输入已接收",
  TRANSCRIBING: "正在转写",
  INFERRING: "正在推理",
  CONTRACT_READY: "合约已生成，正在编译计划",
  CONTRACT_REJECTED: "合约已拒绝",
  PLAN_READY: "计划待执行",
  POLICY_BLOCKED: "策略已阻止",
  AWAITING_CONFIRMATION: "等待人工确认",
  CONFIRMED: "已确认待执行",
  EXECUTING: "正在执行",
  VERIFYING: "正在验证",
  COMPLETED: "已完成",
  BLOCKED: "已阻止",
  CLARIFICATION_REQUIRED: "需要澄清",
  FAILED: "失败",
  CANCELLED: "已取消",
  TRANSCRIPT_READY: "Transcript 待确认",
};

function modeLabel(kind: "inference" | "asr" | "execution", value: string): string {
  if (kind === "inference") return value === "fixture" ? "Fixture Inference" : "Private Model";
  if (kind === "asr") {
    if (value === "disabled") return "ASR Disabled";
    if (value === "fixture") return "ASR Fixture";
    return "ASR HTTP";
  }
  return "Localhost Sandbox";
}

export function Header({
  config,
  connectionState,
}: {
  config: PublicConfig;
  connectionState: ConnectionState;
}) {
  const connectionLabels: Record<ConnectionState, string> = {
    idle: "事件流待命",
    connecting: "事件流连接中",
    connected: "事件流已连接",
    reconnecting: "事件流重连中",
    closed: "事件流已正常关闭",
  };
  return (
    <header className="app-header">
      <div className="brand-block">
        <span className="eyebrow">VOICE → CONTRACT → CONTROLLED ACTION</span>
        <h1>Voice2Task Controlled Browser Demo</h1>
        <p>面向中文语音入口的可验证、受控 Browser Agent Demo</p>
      </div>
      <div className="mode-stack" aria-label="运行模式">
        <span className="mode-badge fixture">{modeLabel("inference", config.inference_mode)}</span>
        <span className="mode-badge">{modeLabel("asr", config.asr_mode)}</span>
        <span className="mode-badge safe">{modeLabel("execution", config.execution_mode)}</span>
        <span className={`connection-label ${connectionState}`}>
          <span className="status-dot" aria-hidden="true" />
          {connectionLabels[connectionState]}
        </span>
      </div>
    </header>
  );
}

const EXAMPLES = [
  "帮我搜索北京明天的天气",
  "打开帮助中心",
  "帮我提取这个页面上的商品价格",
  "把邮箱填进表单里，提交前先问我",
  "帮我打开那个页面",
  "替我完成付款",
];

export function InputPanel({
  config,
  text,
  email,
  inputKind,
  audioFile,
  busy,
  onTextChange,
  onEmailChange,
  onInputKindChange,
  onAudioFile,
  onError,
  onSubmit,
}: {
  config: PublicConfig;
  text: string;
  email: string;
  inputKind: "text" | "audio";
  audioFile: File | null;
  busy: boolean;
  onTextChange: (value: string) => void;
  onEmailChange: (value: string) => void;
  onInputKindChange: (value: "text" | "audio") => void;
  onAudioFile: (file: File | null) => void;
  onError: (code: string, message: string) => void;
  onSubmit: () => void;
}) {
  const fileInput = useRef<HTMLInputElement>(null);
  const recorder = useRef<MediaRecorder | null>(null);
  const stream = useRef<MediaStream | null>(null);
  const mounted = useRef(true);
  const acquisitionGeneration = useRef(0);
  const acquisitionPending = useRef(false);
  const inputKindRef = useRef(inputKind);
  const discardOnStop = useRef(false);
  const errorHandler = useRef(onError);
  const chunks = useRef<Blob[]>([]);
  const [recording, setRecording] = useState(false);
  const audioDisabled = config.asr_mode === "disabled";
  errorHandler.current = onError;
  inputKindRef.current = inputKind;

  const stopTracks = useCallback(() => {
    stream.current?.getTracks().forEach((track) => track.stop());
    stream.current = null;
  }, []);

  const stopRecording = useCallback((discard = false) => {
    acquisitionGeneration.current += 1;
    acquisitionPending.current = false;
    if (discard) discardOnStop.current = true;
    const active = recorder.current;
    recorder.current = null;
    try {
      if (active && active.state !== "inactive") active.stop();
    } catch {
      if (mounted.current) {
        errorHandler.current(
          "MICROPHONE_STOP_FAILED",
          "录音停止失败；已释放 microphone tracks。",
        );
      }
    } finally {
      stopTracks();
      if (mounted.current) setRecording(false);
    }
  }, [stopTracks]);

  useEffect(() => {
    if (inputKind !== "audio") stopRecording(true);
  }, [inputKind, stopRecording]);

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
      stopRecording(true);
    };
  }, [stopRecording]);

  const toggleRecording = async () => {
    if (recording) {
      stopRecording();
      return;
    }
    if (acquisitionPending.current) return;
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") {
      onError("MICROPHONE_UNSUPPORTED", "当前浏览器不支持 microphone recording。");
      return;
    }
    const generation = acquisitionGeneration.current + 1;
    acquisitionGeneration.current = generation;
    acquisitionPending.current = true;
    let acquired: MediaStream | null = null;
    try {
      acquired = await navigator.mediaDevices.getUserMedia({ audio: true });
      if (
        !mounted.current
        || inputKindRef.current !== "audio"
        || generation !== acquisitionGeneration.current
      ) {
        acquired.getTracks().forEach((track) => track.stop());
        return;
      }
      stream.current = acquired;
      chunks.current = [];
      discardOnStop.current = false;
      const active = new MediaRecorder(acquired, { mimeType: "audio/webm" });
      recorder.current = active;
      active.ondataavailable = (event) => chunks.current.push(event.data);
      active.onstop = () => {
        const discard = discardOnStop.current;
        discardOnStop.current = false;
        if (!discard && mounted.current && chunks.current.length > 0) {
          onAudioFile(
            new File(chunks.current, "voice2task-recording.webm", { type: "audio/webm" }),
          );
        }
        chunks.current = [];
        recorder.current = null;
        stopTracks();
        if (mounted.current) setRecording(false);
      };
      active.onerror = () => {
        discardOnStop.current = false;
        chunks.current = [];
        if (mounted.current) {
          errorHandler.current(
            "MICROPHONE_RECORDING_FAILED",
            "录音失败；已释放 microphone tracks。",
          );
        }
        recorder.current = null;
        stopTracks();
        if (mounted.current) setRecording(false);
      };
      active.start();
      if (recorder.current === active) setRecording(true);
    } catch (error) {
      if (generation !== acquisitionGeneration.current || !mounted.current) {
        if (acquired !== null && stream.current !== acquired) {
          acquired.getTracks().forEach((track) => track.stop());
        }
        return;
      }
      discardOnStop.current = false;
      chunks.current = [];
      recorder.current = null;
      stopTracks();
      if (!mounted.current) return;
      setRecording(false);
      const code = error instanceof DOMException && error.name === "NotAllowedError"
        ? "MICROPHONE_PERMISSION_DENIED"
        : "MICROPHONE_START_FAILED";
      const message = code === "MICROPHONE_PERMISSION_DENIED"
        ? "Microphone permission denied；可改用音频上传或文本输入。"
        : "Microphone recording 启动失败；可改用音频上传或文本输入。";
      errorHandler.current(code, message);
    } finally {
      if (generation === acquisitionGeneration.current) {
        acquisitionPending.current = false;
      }
    }
  };

  return (
    <section className="panel input-panel" aria-labelledby="input-heading">
      <div className="panel-heading">
        <div>
          <span className="section-index">01</span>
          <h2 id="input-heading">输入</h2>
        </div>
        <div className="segmented" aria-label="输入类型">
          <button
            type="button"
            className={inputKind === "text" ? "active" : ""}
            aria-pressed={inputKind === "text"}
            onClick={() => onInputKindChange("text")}
          >
            文本
          </button>
          <button
            type="button"
            className={inputKind === "audio" ? "active" : ""}
            aria-pressed={inputKind === "audio"}
            onClick={() => onInputKindChange("audio")}
          >
            音频
          </button>
        </div>
      </div>

      <label htmlFor="profile-email">Profile email</label>
      <input
        id="profile-email"
        type="email"
        value={email}
        onChange={(event) => onEmailChange(event.target.value)}
        autoComplete="off"
      />

      {inputKind === "text" ? (
        <>
          <label htmlFor="command">中文指令</label>
          <textarea
            id="command"
            value={text}
            rows={3}
            onChange={(event) => onTextChange(event.target.value)}
          />
          <div className="example-grid" aria-label="受控 fixture 示例">
            {EXAMPLES.map((example) => (
              <button type="button" className="example-button" key={example} onClick={() => onTextChange(example)}>
                {example}
              </button>
            ))}
          </div>
        </>
      ) : (
        <div className="audio-input">
          <p>
            Audio UI and ASR adapter are implemented. Real ASR requires a separately configured provider.
          </p>
          <input
            ref={fileInput}
            className="visually-hidden"
            type="file"
            disabled={audioDisabled}
            accept="audio/wav,audio/webm,audio/mpeg,.wav,.webm,.mp3"
            onChange={(event) => {
              stopRecording(true);
              onAudioFile(event.target.files?.[0] ?? null);
            }}
          />
          <div className="button-row">
            <button type="button" className="secondary-button" disabled={audioDisabled} onClick={() => fileInput.current?.click()}>
              上传音频
            </button>
            <button type="button" className="secondary-button" disabled={audioDisabled} onClick={() => void toggleRecording()}>
              {recording ? "停止录音" : "开始录音"}
            </button>
          </div>
          <span className="file-name">{audioFile?.name ?? "尚未选择音频"}</span>
        </div>
      )}

      {audioDisabled && (
        <p className="boundary-note">ASR 当前禁用；请使用文本输入。未配置 provider 时不声明真实 ASR 可用。</p>
      )}
      <button
        className="primary-button full-width"
        type="button"
        disabled={busy || (inputKind === "text" ? !text.trim() : audioDisabled || !audioFile)}
        onClick={onSubmit}
      >
        {busy ? "处理中…" : inputKind === "text" ? "生成受控计划" : "上传并转写"}
      </button>
    </section>
  );
}

export function TranscriptPanel({
  session,
  transcript,
  busy,
  onChange,
  onConfirm,
}: {
  session: SessionRecord | null;
  transcript: string;
  busy: boolean;
  onChange: (value: string) => void;
  onConfirm: () => void;
}) {
  return (
    <section className="panel" aria-labelledby="transcript-heading">
      <div className="panel-heading">
        <div>
          <span className="section-index">02</span>
          <h2 id="transcript-heading">Transcript</h2>
        </div>
        {session?.transcript_edited && <span className="state-chip warning">用户已编辑</span>}
      </div>
      {!session ? (
        <p className="empty-state">创建 session 后显示 transcript。</p>
      ) : session.input_kind === "audio" && session.status === "TRANSCRIPT_READY" ? (
        <>
          <label htmlFor="transcript-edit">确认或编辑 transcript</label>
          <textarea
            id="transcript-edit"
            rows={3}
            value={transcript}
            onChange={(event) => onChange(event.target.value)}
          />
          <button className="primary-button" type="button" disabled={busy || !transcript.trim()} onClick={onConfirm}>
            确认 Transcript
          </button>
        </>
      ) : (
        <div className="transcript-value">{session.transcript ?? "—"}</div>
      )}
    </section>
  );
}

export function ContractPanel({ session }: { session: SessionRecord | null }) {
  const contract = session?.contract;
  return (
    <section className="panel" aria-labelledby="contract-heading">
      <div className="panel-heading">
        <div>
          <span className="section-index">03</span>
          <h2 id="contract-heading">Contract</h2>
        </div>
        {contract && (
          <div className="validation-pair">
            <span className="state-chip success">Schema ✓</span>
            <span className="state-chip success">Semantic ✓</span>
          </div>
        )}
      </div>
      {!contract ? (
        <p className="empty-state">等待 Voice2Task 输出 BrowserTaskContract V1。</p>
      ) : (
        <>
          <dl className="key-value-grid">
            <div><dt>task_type</dt><dd>{contract.task_type}</dd></div>
            <div><dt>route</dt><dd>{contract.route}</dd></div>
            <div><dt>safety</dt><dd>{contract.safety.allow ? "允许" : "拒绝"} · {contract.safety.reason}</dd></div>
            <div><dt>confirmation</dt><dd>{contract.confirmation_required ? "需要" : "不需要"}</dd></div>
            <div className="wide"><dt>slots</dt><dd><code>{JSON.stringify(contract.slots)}</code></dd></div>
            <div className="wide"><dt>normalized</dt><dd>{contract.normalized_command}</dd></div>
          </dl>
          <details>
            <summary>查看严格 V1 JSON</summary>
            <pre>{JSON.stringify(contract, null, 2)}</pre>
          </details>
        </>
      )}
    </section>
  );
}

export function PlanPanel({
  session,
  busy,
  onExecute,
  onCancel,
  onDelete,
}: {
  session: SessionRecord | null;
  busy: boolean;
  onExecute: () => void;
  onCancel?: () => void;
  onDelete?: () => void;
}) {
  const plan = session?.plan;
  const canExecute = session?.status === "CONFIRMED"
    || (session?.status === "PLAN_READY" && !plan?.requires_confirmation);
  const canCancel = session !== null && ![
    "EXECUTING",
    "VERIFYING",
    "COMPLETED",
    "BLOCKED",
    "CLARIFICATION_REQUIRED",
    "FAILED",
    "CANCELLED",
  ].includes(session.status);
  const canDelete = session !== null && [
    "COMPLETED",
    "BLOCKED",
    "CLARIFICATION_REQUIRED",
    "FAILED",
    "CANCELLED",
  ].includes(session.status);
  return (
    <section className="panel" aria-labelledby="plan-heading">
      <div className="panel-heading">
        <div>
          <span className="section-index">04</span>
          <h2 id="plan-heading">Execution Plan</h2>
        </div>
        {session && <span className={`state-chip status-${session.status.toLowerCase()}`}>{STATUS_LABELS[session.status] ?? session.status}</span>}
      </div>
      {!plan ? (
        <p className="empty-state">Contract 通过后由受控 compiler 生成计划。</p>
      ) : (
        <>
          <div className="capability-line">
            <span>Capability</span><strong>{plan.capability_id ?? "no_execution"}</strong>
          </div>
          <ol className="action-list">
            {plan.actions.length ? plan.actions.map((action) => (
              <li key={action.action_id}>
                <span className="action-number">{action.action_id.replace("action-", "")}</span>
                <div><strong>{action.kind}</strong><span>{action.locator_id ?? "capability root"}</span></div>
                <code>{action.value_source ?? "trusted registry"}</code>
              </li>
            )) : <li className="no-action">零动作：浏览器不会启动</li>}
          </ol>
          <h3 className="subsection-heading">Postconditions</h3>
          <ul className="action-list postcondition-list">
            {plan.postconditions.map((postcondition, index) => (
              <li key={`${postcondition.check_type}-${index}`}>
                <span className="action-number">P{index + 1}</span>
                <div>
                  <strong>{postcondition.check_type}</strong>
                  <span>{postcondition.locator_id ?? postcondition.capability_id}</span>
                </div>
                <code>Expected: {postcondition.expected_source ?? "trusted registry"}</code>
              </li>
            ))}
          </ul>
          {session.policy && (
            <div className={`policy-callout ${session.policy.allowed ? "allowed" : "guarded"}`}>
              <strong>{session.policy.reason_code}</strong>
              <span>{session.policy.message}</span>
            </div>
          )}
          {canExecute && (
            <button className="primary-button full-width" type="button" disabled={busy} onClick={onExecute}>
              {busy ? "执行中…" : session?.status === "CONFIRMED" ? "执行已确认计划" : "执行计划"}
            </button>
          )}
        </>
      )}
      {canCancel && onCancel && (
        <button className="secondary-button full-width" type="button" disabled={busy} onClick={onCancel}>
          取消 Session
        </button>
      )}
      {canDelete && onDelete && (
        <button className="danger-button full-width" type="button" disabled={busy} onClick={onDelete}>
          删除 Session
        </button>
      )}
    </section>
  );
}

export function ConfirmationModal({
  session,
  open,
  busy,
  onApprove,
  onReject,
}: {
  session: SessionRecord;
  open: boolean;
  busy: boolean;
  onApprove: () => void;
  onReject: () => void;
}) {
  if (!open) return null;
  return (
    <div className="modal-scrim" role="presentation">
      <section className="confirmation-modal" role="dialog" aria-modal="true" aria-label="写操作确认">
        <span className="modal-kicker">HUMAN-IN-THE-LOOP</span>
        <h2>写操作确认</h2>
        <p>即将把 Profile email 填入本地 sandbox DOM。当前 Demo 不访问真实网站、不保存、不提交。</p>
        <ul>
          {session.plan?.actions.map((action) => (
            <li key={action.action_id}><strong>{action.kind}</strong> · {action.capability_id} · {action.locator_id ?? "root"}</li>
          ))}
        </ul>
        <p className="expiry">确认 token 绑定当前 session / plan v{session.plan_version}，五分钟过期且仅可消费一次。</p>
        <div className="modal-actions">
          <button className="danger-button" type="button" disabled={busy} onClick={onReject}>拒绝</button>
          <button className="primary-button" type="button" disabled={busy} onClick={onApprove}>
            {busy ? "处理中…" : "确认计划"}
          </button>
        </div>
      </section>
    </div>
  );
}

export function Timeline({
  events,
  connectionState,
}: {
  events: ExecutionEvent[];
  connectionState: ConnectionState;
}) {
  return (
    <section className="panel timeline-panel" aria-labelledby="timeline-heading">
      <div className="panel-heading">
        <div>
          <span className="section-index">05</span>
          <h2 id="timeline-heading">Execution Timeline</h2>
        </div>
        {connectionState === "reconnecting" && <span className="state-chip warning">正在重连事件流</span>}
      </div>
      {!events.length ? <p className="empty-state">事件将按持久化 seq 实时出现。</p> : (
        <ol className="timeline-list">
          {events.map((event) => (
            <li key={event.seq}>
              <span className={`timeline-marker state-${event.status}`} aria-hidden="true" />
              <div className="timeline-content">
                <div className="timeline-meta"><strong>#{event.seq}</strong><span>{event.stage}</span><time>{new Date(event.created_at).toLocaleTimeString("zh-CN", { hour12: false })}</time></div>
                <div className="timeline-title"><strong>{event.event_type}</strong><span className="text-status">{event.status}</span></div>
                <p>{event.message}</p>
                {Object.keys(event.payload).length > 0 && (
                  <details><summary>事件 payload</summary><pre>{JSON.stringify(event.payload, null, 2)}</pre></details>
                )}
              </div>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}

export function VerifierPanel({ session }: { session: SessionRecord | null }) {
  const verification = session?.verification;
  return (
    <section className="panel" aria-labelledby="verifier-heading">
      <div className="panel-heading">
        <div>
          <span className="section-index">06</span>
          <h2 id="verifier-heading">Verifier</h2>
        </div>
        {verification && (
          <span className={`state-chip ${verification.passed ? "success" : "danger"}`}>
            {verification.passed ? "通过" : "失败"}
          </span>
        )}
      </div>
      {!verification ? <p className="empty-state">执行或 no-execution 终态后显示确定性检查。</p> : (
        <>
          <ul className="check-list">
            {verification.checks.map((check, index) => (
              <li key={`${check.check_type}-${index}`}>
                <span className={`check-symbol ${check.passed ? "pass" : "fail"}`}>{check.passed ? "PASS" : "FAIL"}</span>
                <div><strong>{check.check_type}</strong><span>Expected: <code>{check.expected}</code></span><span>Observed: {check.observed}</span>{check.evidence_ref && <small>{check.evidence_ref}</small>}</div>
              </li>
            ))}
          </ul>
          {session?.execution?.screenshots.map((artifactId) => (
            <figure key={artifactId} className="artifact-preview">
              <img
                src={`/api/sessions/${encodeURIComponent(session.id)}/artifacts/${encodeURIComponent(artifactId)}`}
                alt="本地受控执行截图"
                loading="lazy"
              />
              <figcaption>Session-scoped screenshot · {artifactId.slice(0, 8)}</figcaption>
            </figure>
          ))}
        </>
      )}
    </section>
  );
}

export function SessionHistory({
  sessions,
  selectedId,
  onSelect,
}: {
  sessions: SessionRecord[];
  selectedId: string | null;
  onSelect: (sessionId: string) => void;
}) {
  return (
    <section className="panel history-panel" aria-labelledby="history-heading">
      <div className="panel-heading">
        <div>
          <span className="section-index">07</span>
          <h2 id="history-heading">Session History</h2>
        </div>
        <span className="history-count">{sessions.length}/20</span>
      </div>
      {!sessions.length ? <p className="empty-state">暂无本地 session。</p> : (
        <ul className="history-list">
          {sessions.map((item) => (
            <li key={item.id}>
              <button type="button" className={item.id === selectedId ? "selected" : ""} onClick={() => onSelect(item.id)}>
                <span><strong>{STATUS_LABELS[item.status] ?? item.status}</strong><small>{item.contract?.normalized_command ?? item.transcript ?? "pending"}</small></span>
                <time>{new Date(item.updated_at).toLocaleTimeString("zh-CN", { hour12: false })}</time>
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
