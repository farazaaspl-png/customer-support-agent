const API_URL = import.meta.env.VITE_API_URL || "";

export type AgentStatus =
  | "thinking"
  | "tool_call"
  | "waiting_for_human"
  | "completed"
  | "error";

export interface ChatResponse {
  thread_id: string;
  response: string;
  agent_status: AgentStatus;
  intent?: string;
  title?: string;
  pending_refund?: {
    order_number: string;
    customer_email: string;
    reason: string;
    amount?: number;
    status: string;
  };
}

export interface Session {
  id: string;
  thread_id: string;
  title: string;
  message_count: number;
  summary?: string;
  created_at: string;
  updated_at: string;
}

export interface StoredMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  created_at: string;
}

export async function sendMessage(
  message: string,
  threadId?: string
): Promise<ChatResponse> {
  const res = await fetch(`${API_URL}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, thread_id: threadId }),
  });
  if (!res.ok) throw new Error(`Chat failed: ${res.statusText}`);
  return res.json();
}

export async function listSessions(): Promise<Session[]> {
  const res = await fetch(`${API_URL}/api/sessions`);
  if (!res.ok) throw new Error(`Failed to load sessions: ${res.statusText}`);
  return res.json();
}

export async function loadSessionMessages(threadId: string): Promise<{
  thread_id: string;
  title: string;
  messages: StoredMessage[];
}> {
  const res = await fetch(`${API_URL}/api/sessions/${threadId}/messages`);
  if (!res.ok) throw new Error(`Failed to load messages: ${res.statusText}`);
  return res.json();
}

export async function approveRefund(
  threadId: string,
  approved: boolean
): Promise<void> {
  const res = await fetch(`${API_URL}/api/hitl/approve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ thread_id: threadId, approved }),
  });
  if (!res.ok) throw new Error(`Approve failed: ${res.statusText}`);
}

export async function resumeAfterHitl(threadId: string): Promise<ChatResponse> {
  const res = await fetch(`${API_URL}/api/hitl/resume`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ thread_id: threadId }),
  });
  if (!res.ok) throw new Error(`Resume failed: ${res.statusText}`);
  return res.json();
}
