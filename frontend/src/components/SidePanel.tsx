import type { Session } from "../api";

interface Props {
  sessions: Session[];
  activeThreadId?: string;
  onSelect: (threadId: string) => void;
  onNewChat: () => void;
  loading?: boolean;
}

function formatDate(iso: string) {
  const d = new Date(iso);
  const now = new Date();
  const diff = now.getTime() - d.getTime();
  if (diff < 86400000) return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  return d.toLocaleDateString([], { month: "short", day: "numeric" });
}

export default function SidePanel({
  sessions,
  activeThreadId,
  onSelect,
  onNewChat,
  loading,
}: Props) {
  return (
    <aside className="side-panel">
      <div className="side-panel-header">
        <h2>History</h2>
        <button className="btn-new-chat" onClick={onNewChat} title="New conversation">
          + New
        </button>
      </div>

      <div className="session-list">
        {loading && <p className="session-empty">Loading…</p>}
        {!loading && sessions.length === 0 && (
          <p className="session-empty">No conversations yet</p>
        )}
        {sessions.map((s) => (
          <button
            key={s.thread_id}
            className={`session-item${s.thread_id === activeThreadId ? " active" : ""}`}
            onClick={() => onSelect(s.thread_id)}
          >
            <span className="session-title">{s.title}</span>
            <span className="session-meta">
              {s.message_count} msg · {formatDate(s.updated_at)}
            </span>
          </button>
        ))}
      </div>
    </aside>
  );
}
