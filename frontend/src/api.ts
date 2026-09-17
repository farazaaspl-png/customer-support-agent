const API_URL = import.meta.env.VITE_API_URL || "";

export const USER_STORAGE_KEY = "acme_support_user";

export interface AppUser {
  id: string;
  email: string;
  display_name: string;
}

export function loadStoredUser(): AppUser | null {
  try {
    const raw = localStorage.getItem(USER_STORAGE_KEY);
    return raw ? (JSON.parse(raw) as AppUser) : null;
  } catch {
    return null;
  }
}

export function storeUser(user: AppUser): void {
  localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(user));
}

export function clearStoredUser(): void {
  localStorage.removeItem(USER_STORAGE_KEY);
}

export async function signup(
  email: string,
  password: string,
  displayName?: string
): Promise<AppUser> {
  const res = await fetch(`${API_URL}/api/auth/signup`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      email,
      password,
      display_name: displayName || undefined,
    }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = data.detail;
    throw new Error(
      typeof detail === "string" ? detail : detail?.[0]?.msg || res.statusText
    );
  }
  return data;
}

export async function login(email: string, password: string): Promise<AppUser> {
  const res = await fetch(`${API_URL}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = data.detail;
    throw new Error(
      typeof detail === "string" ? detail : detail?.[0]?.msg || res.statusText
    );
  }
  return data;
}

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
  threadId?: string,
  userId?: string
): Promise<ChatResponse> {
  const res = await fetch(`${API_URL}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, thread_id: threadId, user_id: userId }),
  });
  if (!res.ok) throw new Error(`Chat failed: ${res.statusText}`);
  return res.json();
}

export async function listSessions(userId: string): Promise<Session[]> {
  const res = await fetch(
    `${API_URL}/api/sessions?user_id=${encodeURIComponent(userId)}`
  );
  if (!res.ok) throw new Error(`Failed to load sessions: ${res.statusText}`);
  return res.json();
}

export async function loadSessionMessages(
  threadId: string,
  userId: string
): Promise<{
  thread_id: string;
  title: string;
  messages: StoredMessage[];
}> {
  const res = await fetch(
    `${API_URL}/api/sessions/${threadId}/messages?user_id=${encodeURIComponent(userId)}`
  );
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

export async function resumeAfterHitl(
  threadId: string,
  userId: string
): Promise<ChatResponse> {
  const res = await fetch(`${API_URL}/api/hitl/resume`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ thread_id: threadId, user_id: userId }),
  });
  if (!res.ok) throw new Error(`Resume failed: ${res.statusText}`);
  return res.json();
}
