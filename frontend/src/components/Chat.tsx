import { useState } from "react";
import type { AgentStatus, ChatResponse } from "../api";
import { approveRefund, resumeAfterHitl, sendMessage } from "../api";
import AgentStatusBadge from "./AgentStatus";
import MessageList, { type Message } from "./MessageList";

export default function Chat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [threadId, setThreadId] = useState<string | undefined>();
  const [agentStatus, setAgentStatus] = useState<AgentStatus>("completed");
  const [intent, setIntent] = useState<string | undefined>();
  const [pendingRefund, setPendingRefund] = useState<
    ChatResponse["pending_refund"]
  >();
  const [loading, setLoading] = useState(false);

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
    } catch (err) {
      setAgentStatus("error");
      addMessage("assistant", `HITL error: ${err}`);
    } finally {
      setLoading(false);
    }
  };

  return (
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
  );
}
