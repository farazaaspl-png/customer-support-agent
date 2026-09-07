import { useCallback, useEffect, useState } from "react";
import type { AgentStatus, ChatResponse, Session } from "../api";
import {
  approveRefund,
  listSessions,
  loadSessionMessages,
  resumeAfterHitl,
  sendMessage,
} from "../api";
import AgentStatusBadge from "./AgentStatus";
import MessageList, { type Message } from "./MessageList";
import SidePanel from "./SidePanel";

export default function Chat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [input, setInput] = useState("");
  const [threadId, setThreadId] = useState<string | undefined>();
  const [agentStatus, setAgentStatus] = useState<AgentStatus>("completed");
  const [intent, setIntent] = useState<string | undefined>();
  const [pendingRefund, setPendingRefund] = useState<
    ChatResponse["pending_refund"]
  >();
  const [loading, setLoading] = useState(false);
  const [sessionsLoading, setSessionsLoading] = useState(true);

  const refreshSessions = useCallback(async () => {
    try {
      const data = await listSessions();
      setSessions(data);
    } catch {
      /* ignore */
    } finally {
      setSessionsLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshSessions();
  }, [refreshSessions]);

  const toMessages = (stored: { id: string; role: string; content: string }[]): Message[] =>
    stored.map((m) => ({
      id: m.id,
      role: m.role as "user" | "assistant",
      content: m.content,
    }));

  const handleNewChat = () => {
    setThreadId(undefined);
    setMessages([]);
    setAgentStatus("completed");
    setIntent(undefined);
    setPendingRefund(undefined);
    setInput("");
  };

  const handleSelectSession = async (id: string) => {
    if (id === threadId) return;
    setLoading(true);
    try {
      const data = await loadSessionMessages(id);
      setThreadId(data.thread_id);
      setMessages(toMessages(data.messages));
      setAgentStatus("completed");
      setIntent(undefined);
      setPendingRefund(undefined);
    } catch (err) {
      addMessage("assistant", `Failed to load conversation: ${err}`);
    } finally {
      setLoading(false);
    }
  };

  const addMessage = (role: "user" | "assistant", content: string) => {
    setMessages((prev) => [
      ...prev,
      { id: crypto.randomUUID(), role, content },
    ]);
  };

  const handleSend = async () => {
    const text = input.trim();
    if (!text || loading) return;

    setInput("");
    addMessage("user", text);
    setLoading(true);
    setAgentStatus("thinking");

    try {
      const result = await sendMessage(text, threadId);
      setThreadId(result.thread_id);
      setAgentStatus(result.agent_status);
      setIntent(result.intent);
      setPendingRefund(result.pending_refund);
      addMessage("assistant", result.response);
      refreshSessions();
    } catch (err) {
      setAgentStatus("error");
      addMessage("assistant", `Error: ${err}`);
    } finally {
      setLoading(false);
    }
  };

  const handleHitl = async (approved: boolean) => {
    if (!threadId) return;
    setLoading(true);
    try {
      await approveRefund(threadId, approved);
      const result = await resumeAfterHitl(threadId);
      setAgentStatus(result.agent_status);
      setPendingRefund(undefined);
      addMessage(
        "assistant",
        result.response ||
          (approved ? "Refund approved." : "Refund rejected.")
      );
      refreshSessions();
    } catch (err) {
      setAgentStatus("error");
      addMessage("assistant", `HITL error: ${err}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app-layout">
      <SidePanel
        sessions={sessions}
        activeThreadId={threadId}
        onSelect={handleSelectSession}
        onNewChat={handleNewChat}
        loading={sessionsLoading}
      />

      <div className="chat-container">
        <header className="chat-header">
          <h1>Acme Store Support</h1>
          <AgentStatusBadge status={agentStatus} intent={intent} />
        </header>

        <MessageList messages={messages} />

        {pendingRefund && agentStatus === "waiting_for_human" && (
          <div className="hitl-panel">
            <h3>Refund Approval Required</h3>
            <dl>
              <dt>Order</dt>
              <dd>{pendingRefund.order_number}</dd>
              <dt>Customer</dt>
              <dd>{pendingRefund.customer_email}</dd>
              <dt>Amount</dt>
              <dd>
                {pendingRefund.amount != null
                  ? `$${pendingRefund.amount}`
                  : "TBD"}
              </dd>
              <dt>Reason</dt>
              <dd>{pendingRefund.reason}</dd>
            </dl>
            <div className="hitl-actions">
              <button
                className="btn-approve"
                onClick={() => handleHitl(true)}
                disabled={loading}
              >
                Approve Refund
              </button>
              <button
                className="btn-reject"
                onClick={() => handleHitl(false)}
                disabled={loading}
              >
                Reject
              </button>
            </div>
          </div>
        )}

        <form
          className="chat-input"
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
        >
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about orders, refunds, or policies…"
            disabled={loading}
          />
          <button type="submit" disabled={loading || !input.trim()}>
            Send
          </button>
        </form>
      </div>
    </div>
  );
}
