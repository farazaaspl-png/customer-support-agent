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
  pending_refund?: {
    order_number: string;
    customer_email: string;
    reason: string;
    amount?: number;
    status: string;
  };
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
