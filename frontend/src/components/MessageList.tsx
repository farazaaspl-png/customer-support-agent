export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
}

interface Props {
  messages: Message[];
}

export default function MessageList({ messages }: Props) {
  if (messages.length === 0) {
    return (
      <div className="empty-state">
        <p>👋 Hi! I'm the Acme Store support agent.</p>
        <p className="hint">Try asking about orders, refunds, or our return policy.</p>
        <ul className="examples">
          <li>"What is your return policy?"</li>
          <li>"Where is my order ORD-1001?"</li>
          <li>"I want a refund for order ORD-1001"</li>
        </ul>
      </div>
    );
  }

  return (
    <div className="message-list">
      {messages.map((msg) => (
        <div key={msg.id} className={`message message-${msg.role}`}>
          <div className="message-role">
            {msg.role === "user" ? "You" : "Agent"}
          </div>
          <div className="message-content">{msg.content}</div>
        </div>
      ))}
    </div>
  );
}
