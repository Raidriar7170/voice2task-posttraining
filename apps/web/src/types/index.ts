export type PublicConfig = {
  inference_mode: "fixture" | "private_model";
  asr_mode: "disabled" | "fixture" | "http";
  execution_mode: "sandbox";
  benchmark_kind: "controlled_fixture_e2e_demo";
};

export type Safety = { allow: boolean; reason: string };

export type BrowserTaskContract = {
  task_type: "search" | "navigate" | "form_fill" | "extract" | "clarify" | "blocked";
  route: "search_web" | "open_url" | "fill_form" | "extract_page" | "clarify" | "deny";
  safety: Safety;
  confirmation_required: boolean;
  slots: Record<string, unknown>;
  normalized_command: string;
  language: "zh-CN";
  contract_version: "v1";
};

export type ExecutionAction = {
  action_id: string;
  kind: "navigate" | "fill" | "click" | "extract_text";
  capability_id: string;
  locator_id: string | null;
  value_source: string | null;
  timeout_ms: number;
};

export type Postcondition = {
  check_type: string;
  capability_id: string;
  locator_id: string | null;
  expected_source: string | null;
};

export type ExecutionPlan = {
  plan_id: string;
  session_id: string;
  plan_version: number;
  route: string;
  capability_id: string | null;
  requires_confirmation: boolean;
  actions: ExecutionAction[];
  postconditions: Postcondition[];
  max_actions: number;
  expires_at: string;
};

export type VerificationCheck = {
  check_type: string;
  passed: boolean;
  expected: string;
  observed: string;
  evidence_ref: string | null;
};

export type VerificationResult = {
  passed: boolean;
  checks: VerificationCheck[];
  failure_code: string | null;
};

export type ExecutionEvidence = {
  action_outputs: Record<string, string>;
  dom_snapshot: Record<string, string>;
};

export type ExecutionOutcome = {
  browser_context_created: boolean;
  action_count: number;
  final_url_path: string | null;
  evidence: ExecutionEvidence;
  screenshots: string[];
  elapsed_ms: number;
};

export type PolicyResult = {
  allowed: boolean;
  requires_confirmation: boolean;
  reason_code: string;
  message: string;
};

export type SessionContext = {
  session_id: string;
  profile: { email: string };
  selected_capability: string | null;
  plan_version: number;
  plan_issued_at: string;
};

export type SessionStatus =
  | "CREATED"
  | "INPUT_RECEIVED"
  | "TRANSCRIBING"
  | "TRANSCRIPT_READY"
  | "INFERRING"
  | "CONTRACT_READY"
  | "CONTRACT_REJECTED"
  | "PLAN_READY"
  | "POLICY_BLOCKED"
  | "AWAITING_CONFIRMATION"
  | "CONFIRMED"
  | "EXECUTING"
  | "VERIFYING"
  | "COMPLETED"
  | "BLOCKED"
  | "CLARIFICATION_REQUIRED"
  | "FAILED"
  | "CANCELLED";

export type SessionRecord = {
  id: string;
  created_at: string;
  updated_at: string;
  status: SessionStatus;
  input_kind: "text" | "audio";
  context: SessionContext;
  transcript_original: string | null;
  transcript: string | null;
  transcript_edited: boolean;
  inference_mode: string;
  asr_mode: string;
  execution_mode: string;
  contract: BrowserTaskContract | null;
  contract_validation: Record<string, unknown> | null;
  plan: ExecutionPlan | null;
  policy: PolicyResult | null;
  execution: ExecutionOutcome | null;
  verification: VerificationResult | null;
  error_code: string | null;
  plan_version: number;
  confirmation_status: string;
  confirmation_plan_id: string | null;
  confirmation_expires_at: string | null;
  confirmation_consumed_at: string | null;
  execution_claimed: boolean;
  cancel_requested: boolean;
  last_event_seq: number;
};

export type ExecutionEvent = {
  session_id: string;
  seq: number;
  event_type: string;
  stage: string;
  status: string;
  message: string;
  payload: Record<string, unknown>;
  created_at: string;
};

export type APIErrorBody = {
  error: { code: string; message: string; retryable: boolean };
};

export type CreateSessionResponse = {
  session_id: string;
  session: SessionRecord;
  transcript_confirmation_required: boolean;
};

export type ConfirmationChallenge = {
  confirmation_token: string;
  plan_id: string;
  plan_version: number;
  expires_at: string;
};

export type ConnectionState = "idle" | "connecting" | "connected" | "reconnecting" | "closed";
